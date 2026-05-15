import csv, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from features import compute_features

if len(sys.argv) < 2:
    print("Usage: python extract_features.py <labeled_flows.csv>")
    sys.exit(1)

raw = sorted(csv.DictReader(open(sys.argv[1])), key=lambda r: float(r["start_time"]))

flows = [{"start_time": float(r["start_time"]), "end_time": float(r["end_time"]),
          "total_size": int(r["total_size"]), "total_packets": int(r["total_packets"]),
          "label": r["label"]} for r in raw]

fieldnames = ["total_size", "total_packets", "time_since_last_flow", "flows_last_10s",
              "mean_packet_size_last_10s", "median_packet_size_last_10s", "label"]

with open("feature_matrix.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    for i, flow in enumerate(flows):
        if i == 0:
            continue
        feat = compute_features(flow, flows)
        w.writerow({**feat, "label": flow["label"]})
