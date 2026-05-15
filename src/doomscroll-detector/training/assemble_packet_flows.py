import csv, os, sys, statistics

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import network.interceptor as interceptor
from network.interceptor import packet_callback
from network.network_flow import NetworkFlow
from config import PREPROCESSING_FILTER_DST_IP
from scapy.all import sniff

packet_flows = []

class CsvNetworkFlow(NetworkFlow):
    def save_udp_packet(self, response_data, key):
        if key[2] != PREPROCESSING_FILTER_DST_IP:
            return
        iat_samples = response_data[4]
        median_iat = statistics.median(iat_samples) if iat_samples else None
        packet_flows.append((
            response_data[0], response_data[1],
            key[0], key[1], key[2], key[3],
            response_data[2], response_data[3],
            median_iat,
        ))

if len(sys.argv) < 2:
    print("Usage: python pcap-preprocessing.py <pcap_path>")
    sys.exit(1)

interceptor.seen_udp_packets = CsvNetworkFlow()

sniff(offline=sys.argv[1], prn=packet_callback, store=False)

for key in list(interceptor.seen_udp_packets.data.keys()):
    interceptor.seen_udp_packets.remove(key)

with open("packet_flows.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["start_time", "end_time", "source_ip", "source_port", "destination_ip", "destination_port", "total_size", "total_packets", "median_iat"])
    for flow in packet_flows:
        w.writerow(flow)
