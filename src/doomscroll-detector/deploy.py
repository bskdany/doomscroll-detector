from datetime import datetime
from config import *
import csv
import threading 
from interceptor import intercept_traffic
from detector import detect_doomscrolling
from sqlite import init_db
from logger import logger
from firewall import clear_firewall_blacklist

def main():
    init_db()

    traffic_interceptor_thread = threading.Thread(target=intercept_traffic, daemon=True, name="TrafficInterceptor")

    if(DOOMSCROLLIG_CHECK_ENABLE):
        doomscrolling_detector_thread = threading.Thread(target=detect_doomscrolling, daemon=True, name="DoomscrollingDetector")
        doomscrolling_detector_thread.start()

    traffic_interceptor_thread.start()

    try:
        while True:
            threading.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shuttind down...")
        clear_firewall_blacklist()

if __name__ == "__main__":
    main()