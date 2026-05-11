# Network configs
PACKET_SIZE_THRESHOLD = 10  # requests with less than this amount of packets are not saved
INTERFACE_NAME = "wg0"  # network interface to monitor
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

WIREGUARD_CLIENT_SUBNET = "10.66.66."

# Interceptor configs
INTERCEPTOR_LOG_UDP = False 
INTERCEPTOR_LOG_DNS = False
MONITOR_BANDWIDTH = False 

MONITOR_BANDWIDTH_UPDATE_INTERVAL = 1  # how often to update the bandwidth display, in seconds
MONITOR_BANDWIDTH_SESSION_TIMEOUT = 10  # minutes of inactivity before considering a new session 