import csv, sys
from bisect import bisect_right

if len(sys.argv) < 3:
    print("Usage: python label-assembler.py --flows <preprocessed.csv> --labels <state_log.csv>")
    sys.exit(1)

args = dict(zip(sys.argv[1::2], sys.argv[2::2]))
flows_path = args["--flows"]
labels_path = args["--labels"]

rows = list(csv.DictReader(open(labels_path)))
ts_list = [int(r["timestamp_ms"]) for r in rows]
st_list = [r["state"] for r in rows]

def label(ts_ms):
    i = bisect_right(ts_list, ts_ms) - 1
    return st_list[i] if i >= 0 else "unknown"

flows = list(csv.DictReader(open(flows_path)))

with open("labeled_flows.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=[*flows[0].keys(), "label"])
    w.writeheader()
    for flow in flows:
        w.writerow({**flow, "label": label(int(float(flow["start_time"]) * 1000))})
