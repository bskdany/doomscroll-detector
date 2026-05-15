from scapy.all import sniff, IP, IPv6, Ether, TCP, UDP, wrpcap, DNS, DNSQR, DNSRR
import sqlite3
import csv
import statistics
from datetime import datetime
import threading
import sys
import os
from whois import tag_ip
from config import *
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
class PacketDictionary:
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
            median_iat,        # median inter-packet arrival time
        ))
        conn.commit()
        conn.close()

    def get(self, key):
        with self.lock:
            return self.data.get(key, None)

def packet_get_addr_data(packet):
    if packet.haslayer(IP):
        src = packet[IP].src
        dst = packet[IP].dst
    elif packet.haslayer(IPv6):
        src = packet[IPv6].src
        dst = packet[IPv6].dst
    else:
        src, dst = None, None
    return src, dst

seen_udp_packets = PacketDictionary()

def packet_callback(packet):
    if packet.haslayer(DNS):
        dns_layer = packet[DNS]
        if dns_layer.qr == 1:  # DNS Response
            if dns_layer.haslayer(DNSRR):
                for answer in dns_layer.an:
                    if answer.type == 1:  # A Record (IPv4 address)
                        domain_name = answer.rrname.decode()
                        ip_address = answer.rdata
                        tag_ip(ip_address, domain_name) 
                        if(INTERCEPTOR_LOG_DNS):
                            logger.info(f"Tagged ip {ip_address} with domain {domain_name}")

    if packet.haslayer(UDP):
        src_ip, dst_ip = packet_get_addr_data(packet)

        timestamp = packet.time
        dst_port = packet[UDP].dport
        source_port = packet[UDP].sport
        key = (src_ip, source_port, dst_ip, dst_port)
        prev_data = seen_udp_packets.get(key)
        if prev_data:
            start_time, last_time, total_size, total_packets, iat_samples = prev_data
            iat = float(timestamp) - float(last_time)
            new_samples = (iat_samples + [iat])[-50:]
            seen_udp_packets.set(key, [start_time, timestamp, total_size + len(packet), total_packets + 1, new_samples])
        else:
            seen_udp_packets.set(key, [timestamp, timestamp, len(packet), 1, []])

def intercept_traffic():
    logger.info("Intercepting...")
    try:
        sniff(iface=INTERFACE_NAME, prn=packet_callback, store=False)
    except Exception as e:
        logger.error(f"Error: {e}")
        intercept_traffic()
    
if __name__ == "__main__":
    try:
        intercept_traffic()
    except Exception as e:
        logger.error("Crashed, restarting")
        intercept_traffic()