import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import sqlite3, time
from collections import deque

import joblib
import pandas as pd
from config import *
from logger import logger
from sqlite import DB_PATH
from features import compute_features
from network.throttle import limit_bandwidth, lift_bandwidth_limit

_artifact = joblib.load(INFERENCE_MODEL_PATH)
model = _artifact["model"]
_expected_features = _artifact["features"]

_actual_features = list(compute_features(
    {"start_time": 0.0, "end_time": 0.0, "total_size": 1, "total_packets": 1, "median_iat": 0.0},
    [{"start_time": 0.0, "end_time": 0.0, "total_size": 1, "total_packets": 1, "median_iat": 0.0}],
).keys())
if _actual_features != _expected_features:
    raise RuntimeError(
        f"Feature mismatch — retrain the model.\n"
        f"  Model expects: {_expected_features}\n"
        f"  features.py produces: {_actual_features}"
    )


def get_flows(cursor, since):
    cursor.execute('''
        SELECT start_time, end_time, source_ip, total_size, total_packets, median_iat
        FROM udp
        WHERE destination_ip LIKE ? AND source_port = 443 AND start_time >= ?
        ORDER BY start_time ASC
    ''', (CLIENT_SUBNET + '%', since))
    return [{"start_time": r[0], "end_time": r[1], "source_ip": r[2],
             "total_size": r[3], "total_packets": r[4], "median_iat": r[5]} for r in cursor.fetchall()]


def is_sustained_doomscrolling(history: deque, now: float) -> bool:
    """Returns True if doomscrolling predictions have been sustained long enough."""
    cutoff = now - DOOMSCROLLING_PERSISTENCE_WINDOW
    while history and history[0][0] < cutoff:
        history.popleft()

    if len(history) < DOOMSCROLLING_PERSISTENCE_MIN_PREDICTIONS:
        return False

    doom_fraction = sum(1 for _, doom in history if doom) / len(history)
    return doom_fraction >= DOOMSCROLLING_PERSISTENCE_THRESHOLD


def detect_doomscrolling():
    last_seen = time.time()
    prediction_history: deque[tuple[float, bool]] = deque()
    throttled_ips: set[str] = set()

    while True:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()
        history_since = time.time() - max(DOOMSCROLLING_PERSISTENCE_WINDOW, DOOMSCROLLING_CHECK_ROLLING_WINDOW_SIZE)
        all_flows = get_flows(cursor, history_since)
        conn.close()

        new_flows = [f for f in all_flows if f["start_time"] > last_seen]

        for flow in new_flows:
            prediction = model.predict(pd.DataFrame([compute_features(flow, all_flows)]))[0]
            is_doom = prediction == "doomscrolling"
            prediction_history.append((flow["start_time"], is_doom))
            logger.info(f"[{flow['source_ip']}] {prediction}")

        if new_flows:
            last_seen = new_flows[-1]["start_time"]

        now = time.time()
        if is_sustained_doomscrolling(prediction_history, now):
            active_ips = {f["source_ip"] for f in all_flows}
            new_ips = active_ips - throttled_ips
            for ip in new_ips:
                logger.info(f"Sustained doomscrolling — throttling {ip}")
                limit_bandwidth(ip)
            throttled_ips.update(new_ips)
        else:
            for ip in throttled_ips:
                lift_bandwidth_limit(ip)
            throttled_ips.clear()

        time.sleep(DOOMSCROLLING_CHECK_UPDATE_INTERVAL)


if __name__ == "__main__":
    detect_doomscrolling()
