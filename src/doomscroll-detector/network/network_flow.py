import sqlite3
import statistics
import threading

from config import (
    UDP_TIMEOUT, FLOW_TIMEOUT_MULTIPLIER, FLOW_MIN_TIMEOUT,
    PACKET_SIZE_THRESHOLD, INTERCEPTOR_LOG_UDP, CLIENT_SUBNET,
)
from logger import logger
from sqlite import DB_PATH


def packet_size_to_kb(packet_size):
    return round(packet_size / 1024, 1)


# Aggregates UDP packets into flows.
# A flow ends when no packet arrives within an adaptive idle timeout derived
# from the median inter-packet arrival time (IAT) of that flow:
#   timeout = max(median_IAT * FLOW_TIMEOUT_MULTIPLIER, FLOW_MIN_TIMEOUT)
# Falls back to the fixed UDP_TIMEOUT until at least two packets have arrived.
#
# Stored value layout:
#   [0] start_time   – timestamp of the first packet
#   [1] last_time    – timestamp of the most recent packet
#   [2] total_size   – cumulative byte count
#   [3] total_packets
#   [4] iat_samples  – list of the most recent FLOW_IAT_SAMPLE_WINDOW IAT values
class NetworkFlow:
    def __init__(self, timeout=UDP_TIMEOUT):
        self.data = dict()
        self.timers = dict()
        self.fallback_timeout = timeout
        self.lock = threading.Lock()

    def _adaptive_timeout(self, iat_samples):
        if not iat_samples:
            return self.fallback_timeout
        median_iat = statistics.median(iat_samples)
        return max(median_iat * FLOW_TIMEOUT_MULTIPLIER, FLOW_MIN_TIMEOUT)

    def set(self, key, value):
        with self.lock:
            if key in self.timers:
                self.timers[key].cancel()

            self.data[key] = value
            timeout = self._adaptive_timeout(value[4])
            timer = threading.Timer(timeout, self.remove, args=[key])
            self.timers[key] = timer
            timer.start()

    def remove(self, key):
        with self.lock:
            response_data = self.data.pop(key, None)
            if response_data is None:
                return
            if response_data[3] >= PACKET_SIZE_THRESHOLD:
                self.save_udp_packet(response_data, key)

                if INTERCEPTOR_LOG_UDP:
                    if key[0].startswith(CLIENT_SUBNET):
                        logger.info(f"UDP stream | {key[0]}:{key[1]} -> {key[2]}:{key[3]} | {packet_size_to_kb(response_data[2])}kb")
                    else:
                        logger.info(f"UDP stream | {key[2]}:{key[3]} <- {key[0]}:{key[1]} | {packet_size_to_kb(response_data[2])}kb")

            timer = self.timers.pop(key, None)
            if timer:
                timer.cancel()

    def save_udp_packet(self, response_data, key):
        iat_samples = response_data[4]
        median_iat = statistics.median(iat_samples) if iat_samples else None

        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO udp (start_time, end_time, source_ip, source_port, destination_ip, destination_port, total_size, total_packets, median_iat)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            response_data[0],  # start_time
            response_data[1],  # end_time
            key[0],            # source_ip
            key[1],            # source_port
            key[2],            # destination_ip
            key[3],            # destination_port
            response_data[2],  # total_size
            response_data[3],  # total_packets
            median_iat,
        ))
        conn.commit()
        conn.close()

    def get(self, key):
        with self.lock:
            return self.data.get(key, None)
