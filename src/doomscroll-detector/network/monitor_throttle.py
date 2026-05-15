import time
from config import THROTTLE_INTERFACE, THROTTLE_RATE_KBIT, THROTTLE_TARGET_DROP_PCT
from throttle import parse_tc_stats, get_active_rates


def format_bytes(n: int) -> str:
    if n >= 1024 * 1024:
        return f"{n / 1024 / 1024:.1f}MB"
    if n >= 1024:
        return f"{n / 1024:.1f}KB"
    return f"{n}B"


def monitor_throttle(update_interval: int = 1):
    prev_stats: dict = {}

    while True:
        try:
            current_stats = parse_tc_stats()
            active_rates = get_active_rates()

            print("\033[H\033[J", end="")  # clear screen
            print(
                f"Throttled IPs on {THROTTLE_INTERFACE}  "
                f"(target drop: {THROTTLE_TARGET_DROP_PCT}%  "
                f"initial rate: {THROTTLE_RATE_KBIT}kbit)"
            )
            print("\u2500" * 70)

            if not current_stats:
                print("No active throttles.")
            else:
                print(
                    f"{'Source IP':<20} {'Rate':>8} {'Sent':>10} "
                    f"{'Dropped/s':>10} {'Drop %':>8}"
                )
                print("-" * 70)

                for src_ip, cur in sorted(
                    current_stats.items(),
                    key=lambda x: x[1].get("dropped", 0),
                    reverse=True,
                ):
                    prev = prev_stats.get(src_ip, {})
                    delta_dropped = cur.get("dropped", 0) - prev.get("dropped", 0)
                    delta_sent = cur.get("sent_pkts", 0) - prev.get("sent_pkts", 0)
                    delta_total = delta_sent + delta_dropped

                    pct = (delta_dropped / delta_total * 100) if delta_total > 0 else 0.0
                    rate = active_rates.get(src_ip, THROTTLE_RATE_KBIT)
                    sent_str = format_bytes(cur.get("sent_bytes", 0))

                    print(
                        f"{src_ip:<20} {rate:>6}kbit {sent_str:>10} "
                        f"{delta_dropped:>10} {pct:>7.1f}%"
                    )

            prev_stats = current_stats
            time.sleep(update_interval)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(update_interval)


if __name__ == "__main__":
    monitor_throttle()
