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
SERVER_URL = config("SERVER_URL", default="")
SERVER_PORT = config("SERVER_PORT", default="")
DEVICE_ID = config("DEVICE_ID", default="123456")
UPDATE_FREQUENCY = int(config("UPDATE_FREQUENCY", default="5"))

# Offroad frequency will be UPDATE_FREQUENCY * OFFROAD_UPDATE_FACTOR
OFFROAD_UPDATE_FACTOR = int(config("UPDATE_FREQUENCY", default="12"))

if SERVER_PORT:
    SERVER_URL = f"{SERVER_URL}:{SERVER_PORT}"

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
    def send_gps_data(lat, lon, alt, acc, timestamp, speed, bearing):
        """Send the current GPS data to the server."""
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
            if response.status_code == 200:
                logging.info(f"Data sent: {params}")
                return True
            else:
                logging.error(
                    f"Failed to send data. Status code: {response.status_code}"
                )
                return False
        except Exception as e:
            logging.error(f"Error occurred while sending data: {e}")
            return False


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
        """Get GPS data from gpsLocation."""
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

            final_speed = 1.852 * final_speed

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
                success = True
                for data in stored_data:
                    i, lat, lon, alt, acc, timestamp, speed, bearing = data
                    if not Network.send_gps_data(
                        lat, lon, alt, acc, timestamp, speed, bearing
                    ):
                        success = False

                if success:
                    logging.info("Successfully sent all stored data.")
                    Database.delete_stored_data()
                else:
                    logging.error("Failed to send some stored data.")
            else:
                logging.info("No stored data to send.")

    @staticmethod
    def run():
        try:
            device_state_sm = messaging.SubMaster(["deviceState"])
        except Exception as e:
            logging.error(f"Failed to initialize deviceState SubMaster: {e}")
            return

        try:
            sm = messaging.SubMaster(["gpsLocation"])
        except Exception as e:
            logging.error(f"Failed to initialize SubMaster: {e}")
            return
        
        device_state_sm.update(1000)
        onroad = device_state_sm['deviceState'].started
        offroad_count = 0
        
        if onroad:
            logging.info("Starting onroad!")
        else:
            logging.info("Starting offroad!")

        while True:
            try:
                device_state_sm.update(1000)

                if device_state_sm.updated["deviceState"]:
                    if onroad != device_state_sm['deviceState'].started:
                        # If switching from onroad to offroad or vica versa restart the client.
                        logging.error(f"Switching from offroad to onroad restarting")
                        return
                
                if onroad:
                    # Update SubMaster with 5 second timeout (5000ms)
                    sm.update(5000)

                    gps_data = GPSHandler.get_gps_data(sm)
                else:
                    # Get GPS data using the SubMaster instance
                    time.sleep(UPDATE_FREQUENCY)

                    if offroad_count % OFFROAD_UPDATE_FACTOR == 0:
                        logging.info(f"Currently offroad but allowing update ping.")
                        offroad_count = 0
                        gps_data = None
                    else:
                        offroad_count += 1
                        continue

                timestamp = (
                    datetime.utcnow().isoformat() + "Z"
                )  # Always get the current timestamp

                if gps_data:
                    # Unpack the available GPS data
                    (
                        latitude,
                        longitude,
                        altitude,
                        accuracy,
                        timestamp,
                        speed,
                        bearing,
                    ) = gps_data

                    # Send GPS data with timestamp if internet is available
                    if Network.is_internet_available():
                        if not Network.send_gps_data(
                            latitude,
                            longitude,
                            altitude,
                            accuracy,
                            timestamp,
                            speed,
                            bearing,
                        ):
                            gps_buffer.append(gps_data)
                            logging.info("Storing data locally due to failed send.")
                    else:
                        gps_buffer.append(gps_data)
                        logging.info("No internet, storing data locally.")
                else:
                    # Send only timestamp when GPS data is unavailable
                    if Network.is_internet_available():
                        if not Network.send_gps_data(
                            lat=None,
                            lon=None,
                            alt=None,
                            acc=None,
                            timestamp=timestamp,
                            speed=None,
                            bearing=None,
                        ):
                            gps_buffer.append(
                                (None, None, None, None, timestamp, None, None)
                            )
                            logging.info(
                                "Storing timestamp locally due to failed send."
                            )
                    else:
                        gps_buffer.append(
                            (None, None, None, None, timestamp, None, None)
                        )
                        logging.info(
                            "No GPS data, storing timestamp locally due to no internet."
                        )

                # Flush buffer to local DB if necessary
                if gps_buffer:
                    GPSTrackerApp.flush_buffer()

                # Try to send any stored data when internet becomes available
                GPSTrackerApp.send_stored_data()

                time.sleep(UPDATE_FREQUENCY)
            except Exception as e:
                logging.error(f"Error in GPS tracking loop: {e}")
                time.sleep(10)


if __name__ == "__main__":
    logging.info("Starting GPS tracking service...")
    Database.init_db()  # Initialize the SQLite database
    # 30s startup delay
    time.sleep(30000)
    GPSTrackerApp.run()
