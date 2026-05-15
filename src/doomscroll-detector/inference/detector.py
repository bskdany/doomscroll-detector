import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import sqlite3, time

import joblib
import pandas as pd
from config import *
from logger import logger
from sqlite import DB_PATH
from features import compute_features

model = joblib.load(INFERENCE_MODEL_PATH)


def get_flows(cursor, since):
    cursor.execute('''
        SELECT start_time, end_time, source_ip, total_size, total_packets
        FROM udp
        WHERE destination_ip LIKE ? AND source_port = 443 AND start_time >= ?
        ORDER BY start_time ASC
    ''', (CLIENT_SUBNET + '%', since))
    return [{"start_time": r[0], "end_time": r[1], "source_ip": r[2],
             "total_size": r[3], "total_packets": r[4]} for r in cursor.fetchall()]


def detect_doomscrolling():
    last_seen = time.time()

    while True:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()
        history_since = time.time() - max(DOOMSCROLLING_CHECK_ROLLING_WINDOW_SIZE, 10)
        all_flows = get_flows(cursor, history_since)
        conn.close()

        new_flows = [f for f in all_flows if f["start_time"] > last_seen]

        for flow in new_flows:
            prediction = model.predict(pd.DataFrame([compute_features(flow, all_flows)]))[0]
            logger.info(f"[{flow['source_ip']}] {prediction}")

        if new_flows:
            last_seen = new_flows[-1]["start_time"]

        time.sleep(DOOMSCROLLING_CHECK_UPDATE_INTERVAL)


if __name__ == "__main__":
    detect_doomscrolling()
