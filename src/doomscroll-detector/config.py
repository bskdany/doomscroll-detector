# Network configs
PACKET_SIZE_THRESHOLD = 10  # requests with less than this amount of packets are not saved
INTERFACE_NAME = "tailscale0"  # network interface to monitor
THROTTLE_INTERFACE = "enp2s0"  # internet-facing interface for ingress policing
THROTTLE_RATE_KBIT = 1000      # initial police rate in kbit/s per throttled source IP
THROTTLE_BURST_KB = 64         # burst size in KB for the police action
THROTTLE_TARGET_DROP_PCT = 40  # target packet drop % for the dynamic adjuster
THROTTLE_MIN_RATE_KBIT = 100   # floor rate the adjuster will not go below
THROTTLE_MAX_RATE_KBIT = 5000  # ceiling rate the adjuster will not go above
THROTTLE_ADJUST_INTERVAL = 1   # how often the adjuster runs, in seconds
UDP_TIMEOUT = 0.1              # fallback timeout when fewer than 2 packets have arrived
FLOW_TIMEOUT_MULTIPLIER = 10   # adaptive timeout = median_IAT * this
FLOW_MIN_TIMEOUT = 0.05        # floor for the adaptive timeout, in seconds

# File paths
UDP_LOG_FILE = "./traffic_logs/udp.csv"
TCP_LOG_FILE = "./traffic_logs/tcp.csv"
DNS_LOG_FILE = "./traffic_logs/dns.csv"

# IP filtering
IGNORE_LOCAL_IPS = True  # whether to ignore packets from local IPs (192.168.*)

# QUIC detection
QUIC_DETECT_ENABLE = True
QUIC_DETECT_POLL_INTERVAL = 1   # seconds between polls
QUIC_DETECT_LOOKBACK = 5        # seconds of history to scan per tick

# Doomscrolling detection
DOOMSCROLLIG_CHECK_ENABLE = False
DOOMSCROLLING_CHECK_ROLLING_WINDOW_SIZE = 60  # how many minutes to look back to detect doomscrolling, in seconds
DOOMSCROLLING_CHECK_MIN_DATA_POINTS = 5  # minimum number of bursts required before duty-cycle check kicks in
DOOMSCROLLING_CHECK_UPDATE_INTERVAL = 1  # how often to check for doomscrolling, in seconds
DOOMSCROLLING_BLOCK_ON_DETECT = False    # whether to hard-DROP traffic (iptables) when doomscrolling is detected
DOOMSCROLLING_THROTTLE_ON_DETECT = True  # whether to throttle via tc ingress police when doomscrolling is detected
# Duty-cycle thresholds: fraction of the rolling window that is "active" with bursts.
# Too low  → user is barely active (not doomscrolling, just idle).
# Too high → sustained video stream, not a scroll feed.
# Sweet spot for doomscrolling is typically 0.05 – 0.50.
DOOMSCROLLING_DUTY_CYCLE_MIN = 0.05  # below this → not enough activity
DOOMSCROLLING_DUTY_CYCLE_MAX = 0.50  # above this → likely video stream, not scrolling

CLIENT_SUBNET = "100."  # Tailscale CGNAT range

# Interceptor configs
INTERCEPTOR_LOG_UDP = False 
INTERCEPTOR_LOG_DNS = False

MONITOR_BANDWIDTH_UPDATE_INTERVAL = 1  # how often to update the bandwidth display, in seconds
MONITOR_BANDWIDTH_SESSION_TIMEOUT = 10  # minutes of inactivity before considering a new session