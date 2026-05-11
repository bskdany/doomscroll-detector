import pandas as pd
import time
from firewall import add_firewall_block 
from notifications import send_push_message
from whois import whois
from datetime import datetime
from config import *
from logger import logger
import sqlite3

def packet_size_to_mb(packet_size):
    return round(packet_size / (1024 * 1024), 1)

def analyse_window_instagram(rows):
    seen = dict()

    for row in rows:
        src_ip = row[1]
        dst_ip = row[2]
        src_port = row[3]
        dst_port = row[4]

        key = (src_ip, src_port, dst_ip, dst_port)
        if key not in seen:
            seen[key] = 0
        else:
            seen[key] += 1

    for key in seen:
        if (seen[key] >= DOOMSCROLLING_CHECK_MIN_DATA_POINTS):
            src_ip, src_port, dst_ip, dst_port = key
            add_firewall_block(src_ip, src_port, dst_ip, dst_port, DOOMSCROLLING_CHECK_ROLLING_WINDOW_SIZE)
            return True

    return False

def detect_doomscrolling():

    doomscroll_history = dict()

    while True:
        sqlite_conn = sqlite3.connect('traffic.db')
        cursor = sqlite_conn.cursor()

        end_time = datetime.now().timestamp()
        # this is here so that if doomscrolling is detected for a time period, we don't check for it again
        for user_ip, last_time in doomscroll_history.items():
            start_time = max(end_time - DOOMSCROLLING_CHECK_ROLLING_WINDOW_SIZE, last_time)

            cursor.execute('''
                SELECT 
                    start_time,
                    source_ip,
                    destination_ip,
                    source_port,
                    destination_port,
                    total_size
                FROM udp
                WHERE start_time >= ? 
                AND destination_ip = ?
            ''', (start_time, user_ip))
            rows = cursor.fetchall()

            if len(rows) == 0:
                logger.warn(f"No rows found for user {user_ip}")
                continue
            
            logger.info(f"Found {len(rows)} rows for user {user_ip}")

            if analyse_window_instagram(rows):
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
                total_size
            FROM udp
            WHERE start_time >= ? 
            AND destination_ip LIKE ?
            AND destination_ip NOT IN ({})  
        '''.format(','.join(['?'] * len(used_ips))), 
        [start_time, WIREGUARD_CLIENT_SUBNET + '%'] + 
        used_ips)
        rows = cursor.fetchall()
        sqlite_conn.close()

        ip_dataframes = {}
        for row in rows:
            user_ip = row[2]
            if user_ip not in ip_dataframes:
                ip_dataframes[user_ip] = []
            ip_dataframes[user_ip].append(row)


        for user_ip, user_rows in ip_dataframes.items():
            logger.info(f"Found {len(user_rows)} rows for user {user_ip}")
            if analyse_window_instagram(user_rows):
                logger.info(f"Doomscrolling detected for user {user_ip}")
                doomscroll_history[user_ip] = datetime.now().timestamp()

        time.sleep(DOOMSCROLLING_CHECK_UPDATE_INTERVAL)
                
if __name__ == "__main__":
    detect_doomscrolling()
