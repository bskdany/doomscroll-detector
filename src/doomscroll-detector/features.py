import statistics
from bisect import bisect_left

WINDOW_SECONDS = 10.0

def compute_features(flow, all_flows):
    """
    flow and all_flows entries must be dicts with keys:
        start_time (float), end_time (float), total_size (int), total_packets (int)
    all_flows must be sorted by start_time ascending.
    Returns a flat list of feature values.
    """
    start_times = [f["start_time"] for f in all_flows]
    idx = next(i for i, f in enumerate(all_flows) if f["start_time"] == flow["start_time"] and f["total_size"] == flow["total_size"])

    time_since_last = flow["start_time"] - all_flows[idx - 1]["end_time"] if idx > 0 else 0.0

    lo = bisect_left(start_times, flow["start_time"] - WINDOW_SECONDS)
    window = all_flows[lo:idx + 1]
    pkt_sizes = [f["total_size"] / f["total_packets"] for f in window]

    return {
        "total_size": flow["total_size"],
        "total_packets": flow["total_packets"],
        "time_since_last_flow": time_since_last,
        "flows_last_10s": len(window),
        "mean_packet_size_last_10s": statistics.mean(pkt_sizes),
        "median_packet_size_last_10s": statistics.median(pkt_sizes),
    }
