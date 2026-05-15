import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import *
import threading
from interceptor import intercept_traffic
from sqlite import init_db
from logger import logger
from firewall import clear_firewall_blacklist
from throttle import clear_all_throttles, start_dynamic_adjuster

def main():
    init_db()
    clear_all_throttles()  # clean up any leftover tc rules from a previous run
    # start_dynamic_adjuster()

    traffic_interceptor_thread = threading.Thread(target=intercept_traffic, daemon=True, name="TrafficInterceptor")

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