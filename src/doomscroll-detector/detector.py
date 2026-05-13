import statistics
import time
from firewall import add_firewall_block
from throttle import limit_bandwidth
from datetime import datetime
from config import *
from logger import logger
import sqlite3
from sqlite import DB_PATH


def analyse_window(rows, window_size):
    # flows keyed by client (destination) IP; tuple = (start_t, server_ip, total_size, end_t)
    flows: dict[str, list[tuple[float, str, int, float]]] = {}
    for row in rows:
        flows.setdefault(row[2], []).append((row[0], row[1], row[5], row[6]))

    for client_ip, bursts in flows.items():
        if len(bursts) < DOOMSCROLLING_CHECK_MIN_DATA_POINTS:
            continue

        total_active = sum(end - start for start, _, __, end in bursts)
        duty_cycle = total_active / window_size

        if DOOMSCROLLING_DUTY_CYCLE_MIN <= duty_cycle <= DOOMSCROLLING_DUTY_CYCLE_MAX:
            if DOOMSCROLLING_BLOCK_ON_DETECT:
                add_firewall_block(client_ip, None, None, None, DOOMSCROLLING_CHECK_ROLLING_WINDOW_SIZE)
            if DOOMSCROLLING_THROTTLE_ON_DETECT:
                for server_ip in {b[1] for b in bursts}:
                    limit_bandwidth(server_ip)
            return True, client_ip

    return False, None


def _check_recent_events(cursor, client_ip):
    cursor.execute('''
        SELECT start_time, source_ip, total_size
        FROM udp
        WHERE destination_ip = ?
        ORDER BY start_time DESC
        LIMIT 3
    ''', (client_ip,))
    recent = cursor.fetchall()
    if not recent:
        return

    sizes = [r[2] for r in recent]
    start_times = [r[0] for r in recent]
    gaps = [start_times[i] - start_times[i + 1] for i in range(len(start_times) - 1)]
    median_size = statistics.median(sizes)

    logger.info(
        f"Recent [{client_ip}] last {len(recent)} events — "
        f"mean size: {statistics.mean(sizes) / 1024:.1f} KB, "
        f"median size: {median_size / 1024:.1f} KB"
        + (f", mean gap: {statistics.mean(gaps):.2f}s, median gap: {statistics.median(gaps):.2f}s" if gaps else "")
    )

    if median_size > QUIC_FLOW_REEL_BOUND:
        server_ips = {r[1] for r in recent}
        for server_ip in server_ips:
            logger.info(f"Reel detected for {client_ip} (median {median_size / 1024:.1f} KB > {QUIC_FLOW_REEL_BOUND / 1024:.0f} KB), throttling {server_ip}")
            limit_bandwidth(server_ip)


def detect_doomscrolling():

    doomscroll_history = dict()

    while True:
        sqlite_conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = sqlite_conn.cursor()

        end_time = datetime.now().timestamp()
        for user_ip, last_time in doomscroll_history.items():
            start_time = max(end_time - DOOMSCROLLING_CHECK_ROLLING_WINDOW_SIZE, last_time)

            cursor.execute('''
                SELECT 
                    start_time,
                    source_ip,
                    destination_ip,
                    source_port,
                    destination_port,
                    total_size,
                    end_time
                FROM udp
                WHERE start_time >= ? 
                AND destination_ip = ?
            ''', (start_time, user_ip))
            rows = cursor.fetchall()

            if len(rows) == 0:
                continue

            _check_recent_events(cursor, user_ip)
            actual_window = end_time - start_time
            detected, _ = analyse_window(rows, actual_window)
            if detected:
                logger.info(f"Doomscrolling detected for user {user_ip}")
                doomscroll_history[user_ip] = datetime.now().timestamp()

        start_time = end_time - DOOMSCROLLING_CHECK_ROLLING_WINDOW_SIZE

        used_ips = list(doomscroll_history.keys())
        cursor.execute('''
            SELECT 
                start_time,
                source_ip,
                destination_ip,
                source_port,
                destination_port,
                total_size,
                end_time
            FROM udp
            WHERE start_time >= ? 
            AND destination_ip LIKE ?
            AND destination_ip NOT IN ({})
        '''.format(','.join(['?'] * len(used_ips)) if used_ips else '""'),
        [start_time, CLIENT_SUBNET + '%'] + used_ips)
        rows = cursor.fetchall()
        sqlite_conn.close()

        detected, client_ip = analyse_window(rows, DOOMSCROLLING_CHECK_ROLLING_WINDOW_SIZE)
        if detected:
            logger.info(f"Doomscrolling detected for user {client_ip}")
            _check_recent_events(cursor, client_ip)
            doomscroll_history[client_ip] = datetime.now().timestamp()

        time.sleep(DOOMSCROLLING_CHECK_UPDATE_INTERVAL)
                
if __name__ == "__main__":
    detect_doomscrolling()
