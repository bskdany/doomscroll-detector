import csv, statistics, sys
from bisect import bisect_left

if len(sys.argv) < 2:
    print("Usage: python extract_features.py <labeled_flows.csv>")
    sys.exit(1)

flows = sorted(csv.DictReader(open(sys.argv[1])), key=lambda r: float(r["start_time"]))

start_times = [float(f["start_time"]) for f in flows]

def flows_in_window(i, window=10.0):
    t = start_times[i]
    lo = bisect_left(start_times, t - window)
    return flows[lo:i + 1]

fieldnames = [
    "start_time", "end_time", "source_ip", "source_port", "destination_ip", "destination_port",
    "total_size", "total_packets",
    "time_since_last_flow", "flows_last_10s", "mean_packet_size_last_10s", "median_packet_size_last_10s",
    "label",
]

with open("feature_matrix.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    for i, flow in enumerate(flows):
        window = flows_in_window(i)
        pkt_sizes = [float(fw["total_size"]) / int(fw["total_packets"]) for fw in window]

        time_since_last = float(flow["start_time"]) - float(flows[i - 1]["end_time"]) if i > 0 else None

        w.writerow({
            **{k: flow[k] for k in ["start_time", "end_time", "source_ip", "source_port", "destination_ip", "destination_port", "total_size", "total_packets", "label"]},
            "time_since_last_flow": time_since_last,
            "flows_last_10s": len(window),
            "mean_packet_size_last_10s": statistics.mean(pkt_sizes),
            "median_packet_size_last_10s": statistics.median(pkt_sizes),
        })
