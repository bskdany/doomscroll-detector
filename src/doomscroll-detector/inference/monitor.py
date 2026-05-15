import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import sqlite3, time

import joblib
import pandas as pd
from config import *
from sqlite import DB_PATH
from features import compute_features

_artifact = joblib.load(INFERENCE_MODEL_PATH)
model = _artifact["model"]
_expected_features = _artifact["features"]

_actual_features = list(compute_features(
    {"start_time": 0.0, "end_time": 0.0, "total_size": 1, "total_packets": 1},
    [{"start_time": 0.0, "end_time": 0.0, "total_size": 1, "total_packets": 1}],
).keys())
if _actual_features != _expected_features:
    raise RuntimeError(
        f"Feature mismatch — retrain the model.\n"
        f"  Model expects: {_expected_features}\n"
        f"  features.py produces: {_actual_features}"
    )

REFRESH_INTERVAL = 1


def get_flows(since):
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute('PRAGMA journal_mode=WAL')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT start_time, end_time, source_ip, total_size, total_packets
        FROM udp
        WHERE destination_ip LIKE ? AND source_port = 443 AND start_time >= ?
        ORDER BY start_time ASC
    ''', (CLIENT_SUBNET + '%', since))
    rows = cursor.fetchall()
    conn.close()
    return [{"start_time": r[0], "end_time": r[1], "source_ip": r[2],
             "total_size": r[3], "total_packets": r[4]} for r in rows]


def format_bytes(n):
    if n >= 1024 * 1024:
        return f"{n / 1024 / 1024:.1f}MB"
    if n >= 1024:
        return f"{n / 1024:.1f}KB"
    return f"{n}B"


while True:
    flows = get_flows(time.time() - max(DOOMSCROLLING_PERSISTENCE_WINDOW, 10))

    os.system('clear')
    print(f"Flows — last {DOOMSCROLLING_PERSISTENCE_WINDOW}s\n")

    if len(flows) < 2:
        print("  Waiting for traffic...")
    else:
        now = time.time()
        rows = []
        for i, flow in enumerate(flows):
            if i == 0:
                continue
            feat = compute_features(flow, flows)
            state = model.predict(pd.DataFrame([feat]))[0]
            bw_10s = sum(f["total_size"] for f in flows if now - 10.0 <= f["start_time"] <= flow["start_time"])
            rows.append((flow, feat, state, bw_10s))

        rows.sort(key=lambda r: r[3], reverse=True)

        header = f"  {'Source IP':<18}  {'Size':>8}  {'Duration':>9}  {'T.Since':>8}  {'#5s':>4}  {'Total/5s':>9}  {'Med/5s':>8}  {'Max/5s':>8}  {'State'}"
        print(header)
        print("  " + "-" * (len(header) - 2))
        for flow, feat, state, bw_10s in rows:
            print(
                f"  {flow['source_ip']:<18}  {format_bytes(feat['total_size']):>8}"
                f"  {feat['flow_duration']:>8.2f}s  {feat['time_since_last_flow']:>8.2f}"
                f"  {int(feat['flows_last_5s']):>4}  {format_bytes(int(feat['total_bytes_last_5s'])):>9}"
                f"  {format_bytes(int(feat['median_size_last_5s'])):>8}  {format_bytes(int(feat['max_size_last_5s'])):>8}"
                f"  {state}"
            )

    print(f"\n  Updated {time.strftime('%H:%M:%S')}")
    time.sleep(REFRESH_INTERVAL)
