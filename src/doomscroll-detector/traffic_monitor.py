import sqlite3
import statistics
import time
import os
from config import (
    CLIENT_SUBNET,
    DOOMSCROLLING_CHECK_ROLLING_WINDOW_SIZE,
    THROTTLE_INTERFACE,
    THROTTLE_RATE_KBIT,
)
from throttle import parse_tc_stats, get_active_rates
from sqlite import init_db, DB_PATH

init_db()

REFRESH_INTERVAL = 1


def get_flow_stats(window_size):
    now = time.time()
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute('PRAGMA journal_mode=WAL')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT source_ip, total_size
        FROM udp
        WHERE start_time >= ?
          AND destination_ip LIKE ?
    ''', (now - window_size, CLIENT_SUBNET + '%'))
    window_rows = cursor.fetchall()

    cursor.execute('''
        SELECT source_ip, total_size
        FROM (
            SELECT source_ip, total_size, ROW_NUMBER() OVER (PARTITION BY source_ip ORDER BY start_time DESC) AS rn
            FROM udp
            WHERE destination_ip LIKE ?
        ) WHERE rn <= 3
    ''', (CLIENT_SUBNET + '%',))
    recent_rows = cursor.fetchall()
    conn.close()

    window_sizes: dict[str, list[int]] = {}
    window_bursts: dict[str, int] = {}
    for src_ip, total_size in window_rows:
        window_bursts[src_ip] = window_bursts.get(src_ip, 0) + 1
        if total_size is not None:
            window_sizes.setdefault(src_ip, []).append(total_size)

    recent_sizes: dict[str, list[int]] = {}
    for src_ip, total_size in recent_rows:
        if total_size is not None:
            recent_sizes.setdefault(src_ip, []).append(total_size)

    results = []
    for src_ip, bursts in window_bursts.items():
        ws = window_sizes.get(src_ip, [])
        rs = recent_sizes.get(src_ip, [])
        results.append((
            src_ip,
            bursts,
            statistics.median(ws) if ws else 0,
            statistics.mean(ws) if ws else 0,
            statistics.median(rs) if rs else 0,
            statistics.mean(rs) if rs else 0,
        ))

    results.sort(key=lambda r: r[1], reverse=True)
    return results


def format_bytes(n: int) -> str:
    if n >= 1024 * 1024:
        return f"{n / 1024 / 1024:.1f}MB"
    if n >= 1024:
        return f"{n / 1024:.1f}KB"
    return f"{n}B"


prev_tc_stats: dict = {}

while True:
    flow_results = get_flow_stats(DOOMSCROLLING_CHECK_ROLLING_WINDOW_SIZE)

    try:
        current_tc_stats = parse_tc_stats()
        active_rates = get_active_rates()
    except Exception:
        current_tc_stats = {}
        active_rates = {}

    os.system('clear')

    print(f"Flows — last {DOOMSCROLLING_CHECK_ROLLING_WINDOW_SIZE}s\n")

    if not flow_results:
        print("  No traffic.")
    else:
        print(f"  {'Source IP':<18}  {'Bursts':>6}  {'Med size':>9}  {'Mean size':>9}  {'Med(3)':>8}  {'Mean(3)':>8}")
        print("  " + "-" * 75)
        for src_ip, bursts, med, mean, med3, mean3 in flow_results:
            print(f"  {src_ip:<18}  {bursts:>6}  {format_bytes(int(med)):>9}  {format_bytes(int(mean)):>9}  {format_bytes(int(med3)):>8}  {format_bytes(int(mean3)):>8}")

    print(f"\nThrottles on {THROTTLE_INTERFACE}  (initial rate: {THROTTLE_RATE_KBIT}kbit)\n")

    if not current_tc_stats:
        print("  No active throttles.")
    else:
        print(f"  {'Source IP':<20}  {'Rate':>8}  {'Sent':>10}  {'Dropped/s':>10}")
        print("  " + "-" * 55)
        for src_ip, cur in sorted(current_tc_stats.items(),
                                   key=lambda x: x[1].get('dropped', 0), reverse=True):
            prev = prev_tc_stats.get(src_ip, {})
            delta_dropped = cur.get('dropped', 0) - prev.get('dropped', 0)
            rate = active_rates.get(src_ip, THROTTLE_RATE_KBIT)
            print(f"  {src_ip:<20}  {rate:>6}kbit  "
                  f"{format_bytes(cur.get('sent_bytes', 0)):>10}  "
                  f"{delta_dropped:>10}")

    prev_tc_stats = current_tc_stats

    print(f"\n  Updated {time.strftime('%H:%M:%S')}")
    time.sleep(REFRESH_INTERVAL)
