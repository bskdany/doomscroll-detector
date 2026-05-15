import csv, os, statistics, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import interceptor
from interceptor import PacketDictionary, packet_callback
from scapy.all import sniff

packet_flows = []

class CsvPacketDictionary(PacketDictionary):
    def save_udp_packet(self, response_data, key):
        iats = response_data[4]
        packet_flows.append((
            response_data[0], response_data[1],
            key[0], key[1], key[2], key[3],
            response_data[2], response_data[3],
            statistics.median(iats) if iats else None,
        ))

if len(sys.argv) < 2:
    print("Usage: python pcap-preprocessing.py <pcap_path>")
    sys.exit(1)

interceptor.seen_udp_packets = CsvPacketDictionary()

sniff(offline=sys.argv[1], prn=packet_callback, store=False)

for key in list(interceptor.seen_udp_packets.data.keys()):
    interceptor.seen_udp_packets.remove(key)

with open("preprocessed.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["start_time", "end_time", "source_ip", "source_port", "destination_ip", "destination_port", "total_size", "total_packets", "median_iat"])
    for flow in packet_flows:
        w.writerow(flow)
