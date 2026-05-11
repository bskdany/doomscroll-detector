import re
import socket
import subprocess
import threading
import time
from logger import logger
from config import (
    THROTTLE_INTERFACE,
    THROTTLE_RATE_KBIT,
    THROTTLE_BURST_KB,
    THROTTLE_TARGET_DROP_PCT,
    THROTTLE_MIN_RATE_KBIT,
    THROTTLE_MAX_RATE_KBIT,
    THROTTLE_ADJUST_INTERVAL,
)

# src_ip -> prio (int)
_active_filters: dict[str, int] = {}
# src_ip -> current rate in kbit
_active_rates: dict[str, int] = {}
_lock = threading.Lock()

_next_prio = 100


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"tc command failed: {' '.join(cmd)}\n{result.stderr.strip()}")
    return result


def _ingress_qdisc_exists() -> bool:
    result = subprocess.run(
        ["tc", "qdisc", "show", "dev", THROTTLE_INTERFACE, "ingress"],
        capture_output=True, text=True
    )
    return "ingress" in result.stdout


def _ensure_ingress_qdisc():
    if not _ingress_qdisc_exists():
        _run(["tc", "qdisc", "add", "dev", THROTTLE_INTERFACE, "handle", "ffff:", "ingress"])
        logger.info(f"Created ingress qdisc on {THROTTLE_INTERFACE}")


def _delete_ingress_qdisc():
    if _ingress_qdisc_exists():
        _run(["tc", "qdisc", "del", "dev", THROTTLE_INTERFACE, "ingress"])
        logger.info(f"Removed ingress qdisc from {THROTTLE_INTERFACE}")


def _add_filter(prio: int, src_ip: str, rate_kbit: int):
    _run([
        "tc", "filter", "add",
        "dev", THROTTLE_INTERFACE,
        "parent", "ffff:",
        "protocol", "ip",
        "prio", str(prio),
        "u32",
        "match", "ip", "src", f"{src_ip}/32",
        "police",
        "rate", f"{rate_kbit}kbit",
        "burst", f"{THROTTLE_BURST_KB}kb",
        "drop",
        "flowid", ":1",
    ])


def _del_filter(prio: int):
    _run([
        "tc", "filter", "del",
        "dev", THROTTLE_INTERFACE,
        "parent", "ffff:",
        "prio", str(prio),
    ])


# ── Public API ────────────────────────────────────────────────────────────────

def limit_bandwidth(src_ip: str):
    global _next_prio
    with _lock:
        if src_ip in _active_filters:
            logger.info(f"Throttle already active for {src_ip}, skipping")
            return

        _ensure_ingress_qdisc()

        prio = _next_prio
        _next_prio += 1

        _add_filter(prio, src_ip, THROTTLE_RATE_KBIT)
        _active_filters[src_ip] = prio
        _active_rates[src_ip] = THROTTLE_RATE_KBIT
        logger.info(
            f"Throttle added: {src_ip} → {THROTTLE_RATE_KBIT}kbit "
            f"(prio {prio} on {THROTTLE_INTERFACE} ingress)"
        )


def update_bandwidth_limit(src_ip: str, new_rate_kbit: int):
    with _lock:
        prio = _active_filters.get(src_ip)
        if prio is None:
            return
        _del_filter(prio)
        _add_filter(prio, src_ip, new_rate_kbit)
        _active_rates[src_ip] = new_rate_kbit


def lift_bandwidth_limit(src_ip: str):
    with _lock:
        prio = _active_filters.get(src_ip)
        if prio is None:
            logger.warning(f"No active throttle found for {src_ip}")
            return

        _del_filter(prio)
        del _active_filters[src_ip]
        del _active_rates[src_ip]
        logger.info(f"Throttle removed for {src_ip}")

        if not _active_filters:
            _delete_ingress_qdisc()


def clear_all_throttles():
    with _lock:
        for src_ip in list(_active_filters.keys()):
            prio = _active_filters.pop(src_ip)
            _active_rates.pop(src_ip, None)
            try:
                _del_filter(prio)
                logger.info(f"Throttle cleared for {src_ip}")
            except RuntimeError as e:
                logger.error(f"Failed to clear throttle for {src_ip}: {e}")
        _delete_ingress_qdisc()


def get_active_rates() -> dict[str, int]:
    with _lock:
        return dict(_active_rates)


# ── TC stats parsing ──────────────────────────────────────────────────────────

def _hex_to_ip(hex_str: str) -> str:
    val = int(hex_str, 16)
    return socket.inet_ntoa(val.to_bytes(4, "big"))


def parse_tc_stats() -> dict[str, dict]:
    """
    Returns {src_ip: {"sent_bytes": int, "sent_pkts": int, "dropped": int}}
    for all active police filters on the ingress qdisc.
    """
    result = subprocess.run(
        ["tc", "-s", "filter", "show", "dev", THROTTLE_INTERFACE, "parent", "ffff:"],
        capture_output=True, text=True
    )
    if result.returncode != 0 or not result.stdout.strip():
        return {}

    stats: dict[str, dict] = {}
    current: dict = {}

    for line in result.stdout.splitlines():
        prio_match = re.search(r"pref\s+(\d+)\s+u32", line)
        if prio_match and "fh" in line and "ht divisor" not in line:
            if current.get("src_ip"):
                stats[current["src_ip"]] = current
            current = {"prio": int(prio_match.group(1))}

        match_match = re.search(r"match\s+([0-9a-fA-F]{8})/ffffffff at 12", line)
        if match_match and current:
            try:
                current["src_ip"] = _hex_to_ip(match_match.group(1))
            except Exception:
                pass

        stats_match = re.search(
            r"Sent\s+(\d+)\s+bytes\s+(\d+)\s+pkts\s+\(dropped\s+(\d+)", line
        )
        if stats_match and current:
            current["sent_bytes"] = int(stats_match.group(1))
            current["sent_pkts"] = int(stats_match.group(2))
            current["dropped"] = int(stats_match.group(3))

    if current.get("src_ip"):
        stats[current["src_ip"]] = current

    return stats


# ── Dynamic adjuster ──────────────────────────────────────────────────────────

def _adjuster_loop(
    target_pct: float,
    min_kbit: int,
    max_kbit: int,
    interval: int,
):
    prev_stats: dict[str, dict] = {}

    while True:
        time.sleep(interval)
        try:
            current_stats = parse_tc_stats()

            for src_ip, cur in current_stats.items():
                prev = prev_stats.get(src_ip)
                if prev is None:
                    # first sample — collect baseline, skip adjustment
                    continue

                delta_dropped = cur["dropped"] - prev["dropped"]
                delta_sent = cur["sent_pkts"] - prev["sent_pkts"]
                delta_total = delta_sent + delta_dropped

                if delta_total == 0:
                    # no traffic in this interval — nothing to adjust
                    continue

                actual_pct = delta_dropped / delta_total * 100

                with _lock:
                    current_rate = _active_rates.get(src_ip)
                if current_rate is None:
                    continue

                # proportional adjustment: scale rate so actual_pct → target_pct
                # actual_pct < target → lower rate (more aggressive)
                # actual_pct > target → raise rate (ease off)
                if actual_pct > 0:
                    new_rate = int(current_rate * (target_pct / actual_pct))
                else:
                    # 0% drop → halve the rate to push toward target
                    new_rate = current_rate // 2

                # cap single-step change to 2x / 0.5x to prevent a burst
                # after silence from slamming the rate to a floor/ceiling
                new_rate = max(current_rate // 2, min(current_rate * 2, new_rate))
                new_rate = max(min_kbit, min(max_kbit, new_rate))

                if new_rate != current_rate:
                    try:
                        update_bandwidth_limit(src_ip, new_rate)
                    except RuntimeError as e:
                        logger.error(f"Adjuster: failed to update {src_ip}: {e}")

            prev_stats = current_stats

        except Exception as e:
            logger.error(f"Adjuster loop error: {e}")


def start_dynamic_adjuster(
    target_pct: float = THROTTLE_TARGET_DROP_PCT,
    min_kbit: int = THROTTLE_MIN_RATE_KBIT,
    max_kbit: int = THROTTLE_MAX_RATE_KBIT,
    interval: int = THROTTLE_ADJUST_INTERVAL,
):
    t = threading.Thread(
        target=_adjuster_loop,
        args=(target_pct, min_kbit, max_kbit, interval),
        daemon=True,
        name="ThrottleAdjuster",
    )
    t.start()
    logger.info(
        f"Dynamic adjuster started (target {target_pct}% drop, "
        f"{min_kbit}–{max_kbit}kbit, every {interval}s)"
    )
