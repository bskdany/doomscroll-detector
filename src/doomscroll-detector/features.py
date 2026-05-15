import statistics
from bisect import bisect_left

WINDOW_SECONDS = 5.0

def compute_features(flow, all_flows):
    """
    flow and all_flows entries must be dicts with keys:
        start_time (float), end_time (float), total_size (int), total_packets (int),
        median_iat (float | None)
    all_flows must be sorted by start_time ascending.
    Returns a flat dict of feature values.
    """
    start_times = [f["start_time"] for f in all_flows]
    idx = next(i for i, f in enumerate(all_flows) if f["start_time"] == flow["start_time"] and f["total_size"] == flow["total_size"])

    # Start-time difference to avoid negatives from overlapping concurrent flows
    time_since_last = flow["start_time"] - all_flows[idx - 1]["start_time"] if idx > 0 else 0.0

    lo = bisect_left(start_times, flow["start_time"] - WINDOW_SECONDS)
    window = all_flows[lo:idx + 1]
    w_sizes = [f["total_size"] for f in window]
    w_durations = [f["end_time"] - f["start_time"] for f in window]
    w_iats = [f["median_iat"] for f in window if f.get("median_iat") is not None]

    return {
        "total_size":           flow["total_size"],
        "flow_duration":        flow["end_time"] - flow["start_time"],
        "total_packets":        flow["total_packets"],
        "median_iat":           flow.get("median_iat") or 0.0,
        "time_since_last_flow": time_since_last,
        "flows_last_5s":        len(window),
        "total_bytes_last_5s":  sum(w_sizes),
        "median_size_last_5s":  statistics.median(w_sizes),
        "max_size_last_5s":     max(w_sizes),
        "size_stddev_last_5s":  statistics.stdev(w_sizes) if len(w_sizes) > 1 else 0.0,
        "mean_duration_last_5s": statistics.mean(w_durations),
        "mean_iat_last_5s":     statistics.mean(w_iats) if w_iats else 0.0,
    }
