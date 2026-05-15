import csv
from datetime import datetime
import pandas as pd
from config import *
import sqlite3

def tag_ip(ip, domain):
    conn = sqlite3.connect('traffic.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO dns (timestamp, domain_name, ip_address)
        VALUES (?, ?, ?)
    ''', (datetime.now().timestamp(), domain, ip))
    conn.commit()
    conn.close()
    
def whois(ip):
    conn = sqlite3.connect('traffic.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT domain_name FROM dns WHERE ip_address = ?
    ''', (ip,))
    domain = cursor.fetchone()
    conn.close()
    return domain