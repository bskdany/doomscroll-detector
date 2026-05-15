import subprocess
import threading
import time
from logger import logger

firewall_blacklist = set()

def _add_rule(blacklist_key):
    if(blacklist_key in firewall_blacklist):
        raise Exception(f"Firewall block already exists for {blacklist_key}")
    
    source_ip, source_port, destination_ip, destination_port = blacklist_key

    firewall_blacklist.add(blacklist_key)
    subprocess.run([
        "sudo", "iptables", "-I", "FORWARD",
        "-s", source_ip,
        "-d", destination_ip,
        "-p", "udp",
        "--sport", str(source_port),
        "--dport", str(destination_port),
        "-j", "DROP"
    ])
    logger.info(f"Added block for traffic from {source_ip}:{source_port} to {destination_ip}:{destination_port}")

def _remove_rule(blacklist_key):
    if(blacklist_key not in firewall_blacklist):
        raise Exception(f"Firewall block does not exist for {blacklist_key}")
    
    source_ip, source_port, destination_ip, destination_port = blacklist_key

    firewall_blacklist.remove(blacklist_key)
    subprocess.run([
        "sudo", "iptables", "-D", "FORWARD",
        "-s", source_ip,
        "-d", destination_ip,
        "-p", "udp",
        "--sport", str(source_port),
        "--dport", str(destination_port),
        "-j", "DROP"
    ])
    logger.info(f"Removed block for traffic from {source_ip}:{source_port} to {destination_ip}:{destination_port}")

def _add_firewall_block(source_ip, source_port, destination_ip, destination_port, duration_seconds=10):
    blacklist_key = (source_ip, source_port, destination_ip, destination_port)

    try:
        _add_rule(blacklist_key)
        timer = threading.Timer(duration_seconds, _remove_rule, args=[blacklist_key])
        timer.start()

    except subprocess.CalledProcessError as e:
        logger.error(f"Error setting firewall rule: {e}")
    
def get_firewall_blacklist():
    return firewall_blacklist

def add_firewall_block(source_ip, source_port, destination_ip, destination_port, duration_seconds=10):
    thread = threading.Thread(
        target=_add_firewall_block,
        args=[source_ip, source_port, destination_ip, destination_port, duration_seconds]
    )
    thread.start()

def clear_firewall_blacklist():
    for blacklist_key in firewall_blacklist:
        _remove_rule(blacklist_key)
    firewall_blacklist.clear()