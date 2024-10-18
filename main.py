import requests
import cereal.messaging as messaging
from datetime import datetime
import time
import sqlite3
import logging
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# SQLite database setup
DB_PATH = os.getenv('DB_PATH', 'gps_data.db')

# In-memory buffer
BUFFER_SIZE = int(os.getenv('BUFFER_SIZE', 10))
gps_buffer = []

def init_db():
    """Initialize the SQLite database to store GPS data."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS gps_data
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  lat REAL, lon REAL, altitude REAL, accuracy REAL,
                  timestamp TEXT)''')
    conn.commit()
    conn.close()

def store_gps_data(lat, lon, alt, acc, timestamp):
    """Store GPS data locally in the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO gps_data (lat, lon, altitude, accuracy, timestamp)
                 VALUES (?, ?, ?, ?, ?)''', (lat, lon, alt, acc, timestamp))
    conn.commit()
    conn.close()

def fetch_stored_data():
    """Fetch all locally stored GPS data."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM gps_data')
    rows = c.fetchall()
    conn.close()
    return rows

def delete_stored_data():
    """Delete all locally stored GPS data once successfully sent."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM gps_data')
    conn.commit()
    conn.close()

def send_gps_data_batch(data_batch):
    """Send a batch of GPS data points to the server."""
    url = os.getenv('SERVER_URL', "https://osmand.nzmdn.me/")
    success = True
    for data in data_batch:
        lat, lon, alt, acc, timestamp = data
        params = {
            "deviceid": 971543493196,  # Replace with your actual device ID
            "lat": lat,
            "lon": lon,
            "altitude": alt,
            "accuracy": acc,
            "timestamp": timestamp,
            "speed": 0,
            "bearing": 0,
            "batt": 75  # Example battery level, adjust as needed
        }

        try:
            response = requests.get(url, params=params)
            if response.status_code != 200:
                success = False
                logging.error(f"Failed to send data. Status code: {response.status_code}")
        except Exception as e:
            success = False
            logging.error(f"Error occurred while sending data: {e}")

    return success

def is_internet_available():
    """Check if the internet is available by pinging a reliable server."""
    try:
        response = requests.get('http://www.google.com', timeout=5)
        return response.status_code == 200
    except requests.ConnectionError:
        return False

def get_gps_data():
    """Get GPS data from ubloxRaw messages."""
    gps_socket = messaging.sub_sock('ubloxRaw', conflate=True)
    msg = messaging.recv_one_or_none(gps_socket)
    
    if msg is not None:
        gps = msg.ubloxRaw
        latitude = gps.navPosLlh.lat
        longitude = gps.navPosLlh.lon
        altitude = gps.navPosLlh.height
        accuracy = gps.navPosLlh.hAcc
        timestamp = datetime.utcnow().isoformat() + 'Z'
        return latitude, longitude, altitude, accuracy, timestamp
    return None

def flush_buffer():
    """Flush the in-memory buffer to the SQLite database if there's no internet."""
    for data in gps_buffer:
        lat, lon, alt, acc, timestamp = data
        store_gps_data(lat, lon, alt, acc, timestamp)
    gps_buffer.clear()

def send_stored_data():
    """Attempt to send locally stored data when internet is available."""
    if is_internet_available():
        stored_data = fetch_stored_data()
        if stored_data:
            if send_gps_data_batch(stored_data):
                logging.info("Successfully sent all stored data.")
                delete_stored_data()
            else:
                logging.error("Failed to send stored data.")
        else:
            logging.info("No stored data to send.")

def run_gps_tracker():
    while True:
        try:
            gps_data = get_gps_data()
            if gps_data:
                gps_buffer.append(gps_data)

                # If the buffer is full, attempt to send it or store it locally
                if len(gps_buffer) >= BUFFER_SIZE:
                    if is_internet_available():
                        if send_gps_data_batch(gps_buffer):
                            logging.info("Data sent from buffer.")
                            gps_buffer.clear()  # Clear the buffer after successful send
                        else:
                            logging.error("Failed to send buffer data, storing locally.")
                            flush_buffer()
                    else:
                        logging.info("No internet, storing buffer locally.")
                        flush_buffer()

            # Try to send any stored data when internet becomes available
            send_stored_data()

            time.sleep(5)  # Adjust the frequency of GPS data collection
        except Exception as e:
            logging.error(f"Error in GPS tracking loop: {e}")
            time.sleep(10)  # Retry after a delay in case of errors

if __name__ == "__main__":
    logging.info("Starting GPS tracking service...")
    init_db()  # Initialize the SQLite database
    run_gps_tracker()
