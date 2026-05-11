import pandas as pd
import sqlite3
import time
from config import *

def get_traffic_data(start_time):
    conn = sqlite3.connect('traffic.db')
    
    df = pd.read_sql_query('''
        SELECT 
            start_time as 'Start Time',
            end_time as 'End Time',
            source_ip as 'Source IP',
            source_port as 'Source Port',
            destination_ip as 'Destination IP',
            destination_port as 'Destination Port',
            total_size as 'Total Size'
        FROM udp
        WHERE start_time >= ?
    ''', conn, params=(start_time,))
    
    conn.close()
    return df

def format_size(size_kb):
    if size_kb >= 1024:
        return f"{size_kb/1024:.1f}MB"
    return f"{size_kb:.1f}KB"

def calculate_bandwidth_stats(df):
    if df.empty:
        return {}
        
    bandwidth_stats = {}
    
    # Group by all connection parameters
    for (src_ip, src_port, dst_ip, dst_port), group in df.groupby(['Source IP', 'Source Port', 'Destination IP', 'Destination Port']):
        total_size = group['Total Size'].sum()
        
        conn_key = (src_ip, src_port, dst_ip, dst_port)
        bandwidth_stats[conn_key] = {
            'kb': total_size / 1024  # Convert bytes to kilobytes
        }
    
    return bandwidth_stats

def monitor_bandwidth(update_interval=MONITOR_BANDWIDTH_UPDATE_INTERVAL):
    last_stats = {}

    start_time = time.time()
    
    while True:
        try:
            df = get_traffic_data(start_time)
            current_stats = calculate_bandwidth_stats(df)
            
            print("\033[H\033[J")  # Clear screen
            print(f"{'Source':21} {'Port':>5} {'Destination':21} {'Port':>5} {'Size':>8}")
            print("-" * 63)
            
            # Sort by total KB (bandwidth) in descending order
            for (src_ip, src_port, dst_ip, dst_port), stats in sorted(current_stats.items(), key=lambda x: x[1]['kb'], reverse=True):
                size_str = format_size(stats['kb'])
                print(f"{src_ip:<21} {src_port:>5} {dst_ip:<21} {dst_port:>5} {size_str:>8}")
            
            last_stats = current_stats
            time.sleep(update_interval)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(update_interval)

if __name__ == "__main__":
    monitor_bandwidth()