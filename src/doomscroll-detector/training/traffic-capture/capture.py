#!/usr/bin/env python3
import time
from scapy.all import PcapWriter, sniff

IFACE = "tailscale0"
out_path = f"{int(time.time())}.pcap"
writer = PcapWriter(out_path, append=False, sync=True, linktype=101)  # DLT_RAW for TUN

print(f"Capturing on {IFACE!r} → {out_path}  (Ctrl+C to stop)")
sniff(iface=IFACE, prn=lambda pkt: writer.write(pkt), store=False)
