from scapy.all import sniff, IP, IPv6, UDP, DNS, DNSRR
from network.whois import tag_ip
from config import INTERFACE_NAME, INTERCEPTOR_LOG_DNS
from logger import logger
from network.network_flow import NetworkFlow

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

seen_udp_packets = NetworkFlow()

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