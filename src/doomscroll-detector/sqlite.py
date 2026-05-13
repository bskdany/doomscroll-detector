import sqlite3
import csv
from pathlib import Path

DB_PATH = str(Path(__file__).parent / 'traffic.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS udp (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        start_time REAL,
        end_time REAL,
        source_ip TEXT,
        source_port INTEGER,
        destination_ip TEXT,
        destination_port INTEGER,
        total_size INTEGER,
        total_packets INTEGER,
        median_iat REAL
    )
    ''')

    # migrate existing databases that predate the median_iat column
    try:
        cursor.execute('ALTER TABLE udp ADD COLUMN median_iat REAL')
    except Exception:
        pass  # column already exists

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tcp (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        start_time REAL,
        end_time REAL,
        source_ip TEXT,
        source_port INTEGER,
        destination_ip TEXT,
        destination_port INTEGER,
        total_size INTEGER,
        total_packets INTEGER
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS dns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp REAL,
        domain_name TEXT,
        ip_address TEXT
    )
    ''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()