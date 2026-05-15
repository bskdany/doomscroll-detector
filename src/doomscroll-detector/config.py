# Network configs
PACKET_SIZE_THRESHOLD = 10  # requests with less than this amount of packets are not saved
INTERFACE_NAME = "tailscale0"  # network interface to monitor
THROTTLE_INTERFACE = "enp2s0"  # internet-facing interface for ingress policing
THROTTLE_RATE_KBIT = 150       # initial police rate in kbit/s per throttled source IP
THROTTLE_BURST_KB = 64         # burst size in KB for the police action
THROTTLE_TARGET_DROP_PCT = 40  # target packet drop % for the dynamic adjuster
THROTTLE_MIN_RATE_KBIT = 150   # floor rate the adjuster will not go below
THROTTLE_MAX_RATE_KBIT = 5000  # ceiling rate the adjuster will not go above
THROTTLE_ADJUST_INTERVAL = 1   # how often the adjuster runs, in seconds
UDP_TIMEOUT = 0.1              # fallback timeout when fewer than 2 packets have arrived
FLOW_TIMEOUT_MULTIPLIER = 10   # adaptive timeout = median_IAT * this
FLOW_MIN_TIMEOUT = 0.05        # floor for the adaptive timeout, in seconds

CLIENT_SUBNET = "100."  # Tailscale CGNAT range

# Interceptor configs
INTERCEPTOR_LOG_UDP = False
INTERCEPTOR_LOG_DNS = False

MONITOR_BANDWIDTH_UPDATE_INTERVAL = 1  # how often to update the bandwidth display, in seconds

# Preprocessing
PREPROCESSING_FILTER_DST_IP = "100.91.91.72"  # only flows with this as destination are kept

# Inference
from pathlib import Path
INFERENCE_MODEL_PATH = str(Path(__file__).parent / "training" / "model.joblib")

# Doomscrolling detection
DOOMSCROLLING_CHECK_ROLLING_WINDOW_SIZE = 60  # seconds of history to consider per detection tick
DOOMSCROLLING_CHECK_UPDATE_INTERVAL = 1       # how often to run the detection loop, in seconds

# Persistence: how long and how consistently the model must predict doomscrolling
# before any action is taken. Keeps individual noisy predictions from triggering throttles.
DOOMSCROLLING_PERSISTENCE_WINDOW = 30           # seconds of prediction history to consider
DOOMSCROLLING_PERSISTENCE_THRESHOLD = 0.60      # fraction of predictions that must be doomscrolling
DOOMSCROLLING_PERSISTENCE_MIN_PREDICTIONS = 3   # don't act until we have at least this many predictions