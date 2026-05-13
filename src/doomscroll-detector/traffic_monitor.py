import sqlite3
import statistics
import time
import os
from config import (
    CLIENT_SUBNET,
    DOOMSCROLLING_CHECK_ROLLING_WINDOW_SIZE,
    DOOMSCROLLING_DUTY_CYCLE_MIN,
    DOOMSCROLLING_DUTY_CYCLE_MAX,
    THROTTLE_INTERFACE,
    THROTTLE_RATE_KBIT,
    THROTTLE_TARGET_DROP_PCT,
)
from throttle import parse_tc_stats, get_active_rates
from sqlite import init_db, DB_PATH

init_db()

REFRESH_INTERVAL = 1  # seconds


def get_duty_cycles(window_size):
    now = time.time()
    window_start = now - window_size

    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute('PRAGMA journal_mode=WAL')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT source_ip, destination_ip, start_time, end_time, total_size
        FROM udp
        WHERE start_time >= ?
          AND destination_ip LIKE ?
    ''', (window_start, CLIENT_SUBNET + '%'))
    rows = cursor.fetchall()
    conn.close()

    flows: dict[str, list[tuple[float, float]]] = {}
    sizes: dict[str, list[int]] = {}
    for src_ip, dst_ip, start_t, end_t, total_size in rows:
        flows.setdefault(src_ip, []).append((start_t, end_t))
        if total_size is not None:
            sizes.setdefault(src_ip, []).append(total_size)

    results = []
    for src_ip, bursts in flows.items():
        total_active = sum(end - start for start, end in bursts)
        duty_cycle = total_active / window_size
        src_sizes = sizes.get(src_ip, [])
        median_size = statistics.median(src_sizes) if src_sizes else 0
        results.append((src_ip, duty_cycle, len(bursts), total_active, median_size))

    results.sort(key=lambda r: r[2], reverse=True)
    return results


def format_bytes(n: int) -> str:
    if n >= 1024 * 1024:
        return f"{n / 1024 / 1024:.1f}MB"
    if n >= 1024:
        return f"{n / 1024:.1f}KB"
    return f"{n}B"


def bar(duty_cycle, width=30):
    filled = round(duty_cycle * width)
    return '[' + '#' * filled + '-' * (width - filled) + ']'


prev_tc_stats: dict = {}

while True:
    duty_results = get_duty_cycles(DOOMSCROLLING_CHECK_ROLLING_WINDOW_SIZE)

    try:
        current_tc_stats = parse_tc_stats()
        active_rates = get_active_rates()
    except Exception:
        current_tc_stats = {}
        active_rates = {}

    os.system('clear')

    # ── Duty cycle ────────────────────────────────────────────────────────────
    print(f"Duty cycle — last {DOOMSCROLLING_CHECK_ROLLING_WINDOW_SIZE}s  "
          f"(doomscroll range: {DOOMSCROLLING_DUTY_CYCLE_MIN:.0%} – {DOOMSCROLLING_DUTY_CYCLE_MAX:.0%})\n")

    if not duty_results:
        print("  No traffic.")
    else:
        print(f"  {'Source IP':<18}  {'Duty cycle':>10}  {'Bursts':>6}  {'Active':>8}  {'Med size':>9}")
        print("  " + "-" * 80)
        for src_ip, dc, bursts, active, median_size in duty_results:
            flag = '  <-- !' if DOOMSCROLLING_DUTY_CYCLE_MIN <= dc <= DOOMSCROLLING_DUTY_CYCLE_MAX else ''
            print(f"  {src_ip:<18}  {dc:>9.1%}  {bursts:>6}  {active:>7.1f}s  {format_bytes(int(median_size)):>9}  {bar(dc)}{flag}")

    # ── Throttles ─────────────────────────────────────────────────────────────
    print(f"\nThrottles on {THROTTLE_INTERFACE}  "
          f"(target drop: {THROTTLE_TARGET_DROP_PCT}%  initial rate: {THROTTLE_RATE_KBIT}kbit)\n")

    if not current_tc_stats:
        print("  No active throttles.")
    else:
        print(f"  {'Source IP':<20}  {'Rate':>8}  {'Sent':>10}  {'Dropped/s':>10}  {'Drop %':>7}")
        print("  " + "-" * 65)
        for src_ip, cur in sorted(current_tc_stats.items(),
                                   key=lambda x: x[1].get('dropped', 0), reverse=True):
            prev = prev_tc_stats.get(src_ip, {})
            delta_dropped = cur.get('dropped', 0) - prev.get('dropped', 0)
            delta_sent    = cur.get('sent_pkts', 0) - prev.get('sent_pkts', 0)
            delta_total   = delta_sent + delta_dropped
            pct  = (delta_dropped / delta_total * 100) if delta_total > 0 else 0.0
            rate = active_rates.get(src_ip, THROTTLE_RATE_KBIT)
            print(f"  {src_ip:<20}  {rate:>6}kbit  "
                  f"{format_bytes(cur.get('sent_bytes', 0)):>10}  "
                  f"{delta_dropped:>10}  {pct:>6.1f}%")

    prev_tc_stats = current_tc_stats

    print(f"\n  Updated {time.strftime('%H:%M:%S')}")
    time.sleep(REFRESH_INTERVAL)
