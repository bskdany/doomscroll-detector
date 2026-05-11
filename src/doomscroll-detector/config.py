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
UDP_TIMEOUT = 0.1  # timeout for UDP packet aggregation

# File paths
UDP_LOG_FILE = "./traffic_logs/udp.csv"
TCP_LOG_FILE = "./traffic_logs/tcp.csv"
DNS_LOG_FILE = "./traffic_logs/dns.csv"

# IP filtering
IGNORE_LOCAL_IPS = True  # whether to ignore packets from local IPs (192.168.*)

# Doomscrolling detection
DOOMSCROLLIG_CHECK_ENABLE = True
DOOMSCROLLING_CHECK_ROLLING_WINDOW_SIZE = 60  # how many minutes to look back to detect doomscrolling, in seconds
DOOMSCROLLING_CHECK_MIN_DATA_POINTS = 5  # minimum number of data points to consider a user as doomscrolling
DOOMSCROLLING_CHECK_UPDATE_INTERVAL = 1  # how often to check for doomscrolling, in seconds
DOOMSCROLLING_BLOCK_ON_DETECT = False    # whether to hard-DROP traffic (iptables) when doomscrolling is detected
DOOMSCROLLING_THROTTLE_ON_DETECT = True  # whether to throttle via tc ingress police when doomscrolling is detected

CLIENT_SUBNET = "100."  # Tailscale CGNAT range

# Interceptor configs
INTERCEPTOR_LOG_UDP = False 
INTERCEPTOR_LOG_DNS = False

MONITOR_BANDWIDTH_UPDATE_INTERVAL = 1  # how often to update the bandwidth display, in seconds
MONITOR_BANDWIDTH_SESSION_TIMEOUT = 10  # minutes of inactivity before considering a new session