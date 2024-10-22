import requests
import cereal.messaging as messaging
from datetime import datetime
import time
import sqlite3
import logging
import math
from decouple import config

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Constants
DB_PATH = config("DB_PATH", default="gps_data.db")
BUFFER_SIZE = int(config("BUFFER_SIZE", default=10))
SERVER_URL = config("SERVER_URL", default="https://osmand.nzmdn.me/")
DEVICE_ID = config("DEVICE_ID", default="971543493196")
UPDATE_FREQUENCY = int(config("UPDATE_FREQUENCY", default="5"))

gps_buffer = []
previous_lat = None
previous_lon = None


### Database Management ###
class Database:
    @staticmethod
    def init_db():
        """Initialize the SQLite database to store GPS data."""
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute(
                """CREATE TABLE IF NOT EXISTS gps_data
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                        lat REAL, lon REAL, altitude REAL, accuracy REAL,
                        timestamp TEXT, speed REAL, bearing REAL)"""
            )
            conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Database initialization error: {e}")
        finally:
            conn.close()

    @staticmethod
    def store_gps_data(lat, lon, alt, acc, timestamp, speed, bearing):
        """Store GPS data locally in the SQLite database."""
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute(
                """INSERT INTO gps_data (lat, lon, altitude, accuracy, timestamp, speed, bearing)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (lat, lon, alt, acc, timestamp, speed, bearing),
            )
            conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Error while storing data: {e}")
        finally:
            conn.close()

    @staticmethod
    def fetch_stored_data():
        """Fetch all locally stored GPS data."""
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT * FROM gps_data")
            rows = c.fetchall()
            return rows
        except sqlite3.Error as e:
            logging.error(f"Error while fetching data: {e}")
        finally:
            conn.close()

    @staticmethod
    def delete_stored_data():
        """Delete all locally stored GPS data once successfully sent."""
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("DELETE FROM gps_data")
            conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Error while deleting stored data: {e}")
        finally:
            conn.close()


### Networking ###
class Network:
    @staticmethod
    def is_internet_available():
        """Check if the internet is available by pinging a reliable server."""
        try:
            response = requests.get("http://www.google.com", timeout=5)
            return response.status_code == 200
        except requests.ConnectionError:
            return False

    @staticmethod
    def send_gps_data_batch(data_batch):
        """Send a batch of GPS data points to the server."""
        success = True
        for data in data_batch:
            lat, lon, alt, acc, timestamp, speed, bearing = data
            params = {
                "deviceid": DEVICE_ID,
                "lat": lat,
                "lon": lon,
                "altitude": alt,
                "accuracy": acc,
                "timestamp": timestamp,
                "speed": speed,
                "bearing": bearing if bearing is not None else 0,
            }

            try:
                response = requests.get(SERVER_URL, params=params)
                if response.status_code != 200:
                    success = False
                    logging.error(
                        f"Failed to send data. Status code: {response.status_code}"
                    )
            except Exception as e:
                success = False
                logging.error(f"Error occurred while sending data: {e}")

        return success


### GPS and Data Management ###
class GPSHandler:
    @staticmethod
    def calculate_bearing(lat1, lon1, lat2, lon2):
        """Calculate the bearing between two GPS coordinates."""
        d_lon = math.radians(lon2 - lon1)
        lat1 = math.radians(lat1)
        lat2 = math.radians(lat2)

        x = math.sin(d_lon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(
            lat2
        ) * math.cos(d_lon)

        bearing = math.atan2(x, y)
        bearing = math.degrees(bearing)
        bearing = (bearing + 360) % 360  # Normalize to 0-360 degrees

        return bearing

    @staticmethod
    def get_gps_data(sm):
        """Get GPS data including speed, bearing, and battery level from gpsLocation."""
        global previous_lat, previous_lon

        # Check if gpsLocation is updated
        if sm.updated["gpsLocation"]:
            gps = sm["gpsLocation"]
            latitude = gps.latitude
            longitude = gps.longitude
            altitude = gps.altitude
            speed = gps.speed
            bearing = gps.bearingDeg
            accuracy = gps.horizontalAccuracy
            timestamp = datetime.utcnow().isoformat() + "Z"

            # Extract velocity components (vNED - North, East, Down)
            vel_n, vel_e, vel_d = gps.vNED

            # Update previous GPS position
            previous_lat = latitude
            previous_lon = longitude

            # Calculate speed from velocity components (Pythagorean theorem) if needed
            calculated_speed = (vel_n**2 + vel_e**2 + vel_d**2) ** 0.5

            # Choose speed from gpsLocation or calculate it if not present
            final_speed = speed if speed is not None and speed > 0 else calculated_speed

            return (
                latitude,
                longitude,
                altitude,
                accuracy,
                timestamp,
                final_speed,
                bearing,
            )
        return None


### Core App Logic ###
class GPSTrackerApp:
    @staticmethod
    def flush_buffer():
        """Flush the in-memory buffer to the SQLite database if there's no internet."""
        for data in gps_buffer:
            lat, lon, alt, acc, timestamp, speed, bearing = data
            Database.store_gps_data(lat, lon, alt, acc, timestamp, speed, bearing)
        gps_buffer.clear()

    @staticmethod
    def send_stored_data():
        """Attempt to send locally stored data when internet is available."""
        if Network.is_internet_available():
            stored_data = Database.fetch_stored_data()
            if stored_data:
                if Network.send_gps_data_batch(stored_data):
                    logging.info("Successfully sent all stored data.")
                    Database.delete_stored_data()
                else:
                    logging.error("Failed to send stored data.")
            else:
                logging.info("No stored data to send.")

    @staticmethod
    def run():
        try:
            sm = messaging.SubMaster(["gpsLocation", "deviceState"])
        except Exception as e:
            logging.error(f"Failed to initialize SubMaster: {e}")
            return

        while True:
            try:
                # Update SubMaster every 5 seconds (5000ms)
                sm.update(5000)

                # Get GPS data using the SubMaster instance
                gps_data = GPSHandler.get_gps_data(sm)

                logging.info(gps_data)

                if gps_data:
                    gps_buffer.append(gps_data)

                    # If the buffer is full, attempt to send it or store it locally
                    if len(gps_buffer) >= BUFFER_SIZE:
                        if Network.is_internet_available():
                            if Network.send_gps_data_batch(gps_buffer):
                                logging.info("Data sent from buffer.")
                                gps_buffer.clear()  # Clear the buffer after successful send
                            else:
                                logging.error(
                                    "Failed to send buffer data, storing locally."
                                )
                                GPSTrackerApp.flush_buffer()
                        else:
                            logging.info("No internet, storing buffer locally.")
                            GPSTrackerApp.flush_buffer()

                # Try to send any stored data when internet becomes available
                GPSTrackerApp.send_stored_data()

                time.sleep(UPDATE_FREQUENCY)
            except Exception as e:
                logging.error(f"Error in GPS tracking loop: {e}")
                time.sleep(10)  # Retry after a delay in case of errors


if __name__ == "__main__":
    logging.info("Starting GPS tracking service...")
    Database.init_db()  # Initialize the SQLite database
    GPSTrackerApp.run()
