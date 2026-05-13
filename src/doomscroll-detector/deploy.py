from config import *
import threading
from interceptor import intercept_traffic
from quic_detector import detect_quic
from sqlite import init_db
from logger import logger
from firewall import clear_firewall_blacklist
from throttle import clear_all_throttles, start_dynamic_adjuster

def main():
    init_db()
    clear_all_throttles()  # clean up any leftover tc rules from a previous run
    # start_dynamic_adjuster()

    traffic_interceptor_thread = threading.Thread(target=intercept_traffic, daemon=True, name="TrafficInterceptor")

    if QUIC_DETECT_ENABLE:
        quic_detector_thread = threading.Thread(target=detect_quic, daemon=True, name="QuicDetector")
        quic_detector_thread.start()

    traffic_interceptor_thread.start()

    try:
        while True:
            threading.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shuttind down...")
        clear_firewall_blacklist()
        clear_all_throttles()

if __name__ == "__main__":
    main()