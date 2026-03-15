import asyncio
import httpx
import cereal.messaging as messaging
from datetime import datetime, timezone
import sqlite3
import logging
import math
from decouple import config
from typing import Optional, List, Tuple, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Constants / Configuration
DB_PATH = config("DB_PATH", default="gps_data.db")
BUFFER_SIZE = int(config("BUFFER_SIZE", default=10))
SERVER_URL = config("SERVER_URL", default="")
SERVER_PORT = config("SERVER_PORT", default="")
DEVICE_ID = config("DEVICE_ID", default="123456")
UPDATE_FREQUENCY = int(config("UPDATE_FREQUENCY", default="10"))
OFFROAD_UPDATE_FACTOR = int(config("OFFROAD_UPDATE_FACTOR", default="12"))
STARTUP_DELAY = int(config("STARTUP_DELAY", default="120"))
MAX_RECORDS = int(config("MAX_RECORDS", default="1000"))

if SERVER_PORT:
    SERVER_URL = f"{SERVER_URL}:{SERVER_PORT}"

### Database Management ###
class Database:
    @staticmethod
    def get_connection():
        return sqlite3.connect(DB_PATH)

    @classmethod
    def init_db(cls):
        """Initialize the SQLite database to store GPS data."""
        try:
            with cls.get_connection() as conn:
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS gps_data
                            (id INTEGER PRIMARY KEY AUTOINCREMENT,
                            lat REAL, lon REAL, altitude REAL, accuracy REAL,
                            timestamp TEXT, speed REAL, bearing REAL)"""
                )
        except sqlite3.Error as e:
            logging.error(f"Database initialization error: {e}")

    @classmethod
    def store_gps_data(cls, data_list: List[Tuple]):
        """Store multiple GPS data points locally in the SQLite database and enforce size limits."""
        if not data_list:
            return
        try:
            with cls.get_connection() as conn:
                conn.executemany(
                    """INSERT INTO gps_data (lat, lon, altitude, accuracy, timestamp, speed, bearing)
                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    data_list,
                )
                # Enforce record limit: delete oldest if we exceed MAX_RECORDS
                conn.execute(
                    f"DELETE FROM gps_data WHERE id NOT IN (SELECT id FROM gps_data ORDER BY id DESC LIMIT {MAX_RECORDS})"
                )
        except sqlite3.Error as e:
            logging.error(f"Error while storing data: {e}")

    @classmethod
    def fetch_stored_data(cls) -> List[Tuple]:
        """Fetch all locally stored GPS data."""
        try:
            with cls.get_connection() as conn:
                cursor = conn.execute("SELECT id, lat, lon, altitude, accuracy, timestamp, speed, bearing FROM gps_data")
                return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Error while fetching data: {e}")
            return []

    @classmethod
    def delete_stored_data(cls, ids: List[int]):
        """Delete specific locally stored GPS data once successfully sent."""
        if not ids:
            return
        try:
            with cls.get_connection() as conn:
                conn.execute(f"DELETE FROM gps_data WHERE id IN ({','.join(['?']*len(ids))})", ids)
        except sqlite3.Error as e:
            logging.error(f"Error while deleting stored data: {e}")


### Networking ###
class Network:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)

    async def close(self):
        await self.client.aclose()

    async def send_gps_data(self, lat: Optional[float], lon: Optional[float], alt: Optional[float], 
                          acc: Optional[float], timestamp: str, speed: Optional[float], 
                          bearing: Optional[float]) -> bool:
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
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        try:
            response = await self.client.get(SERVER_URL, params=params)
            if response.status_code == 200:
                logging.info(f"Data sent: {params}")
                return True
            else:
                logging.error(f"Failed to send data. Status code: {response.status_code}")
                return False
        except Exception as e:
            logging.debug(f"Connection error while sending data: {e}")
            return False


### GPS and Data Management ###
class GPSHandler:
    @staticmethod
    def get_gps_data(sm: messaging.SubMaster) -> Optional[Tuple]:
        """Get GPS data from gpsLocation SubMaster."""
        if sm.updated["gpsLocation"]:
            gps = sm["gpsLocation"]
            timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            # Extract velocity components
            vel_n, vel_e, vel_d = gps.vNED
            calculated_speed = (vel_n**2 + vel_e**2 + vel_d**2) ** 0.5
            
            # Choose speed from gpsLocation or calculate it, converted to km/h (1.852 factor suggests knots to km/h)
            # Actually gps.speed is usually m/s in cereal. 1.852 * m/s is NOT km/h. 3.6 * m/s is km/h.
            # The original code used 1.852 * final_speed. 1.852 is knots to km/h. 
            # If gps.speed is in knots, then it's correct. If it's m/s, it should be 3.6.
            # Assuming knots based on original code's 1.852 factor.
            final_speed = (gps.speed if gps.speed is not None and gps.speed > 0 else calculated_speed) * 1.852

            return (
                gps.latitude,
                gps.longitude,
                gps.altitude,
                gps.horizontalAccuracy,
                timestamp,
                final_speed,
                gps.bearingDeg,
            )
        return None


### Core App Logic ###
class GPSTrackerApp:
    def __init__(self):
        self.gps_buffer = []
        self.network = Network()
        self.onroad = False
        self.offroad_count = 0

    async def send_stored_data(self):
        """Attempt to send locally stored data when possible."""
        stored_data = Database.fetch_stored_data()
        if not stored_data:
            return

        logging.info(f"Attempting to send {len(stored_data)} stored records...")
        successfully_sent_ids = []
        
        for data in stored_data:
            db_id, lat, lon, alt, acc, timestamp, speed, bearing = data
            if await self.network.send_gps_data(lat, lon, alt, acc, timestamp, speed, bearing):
                successfully_sent_ids.append(db_id)
            else:
                # If one fails, stop and try again later to preserve order and avoid redundant failures
                break

        if successfully_sent_ids:
            Database.delete_stored_data(successfully_sent_ids)
            logging.info(f"Successfully sent {len(successfully_sent_ids)} stored records.")

    async def run(self):
        Database.init_db()
        logging.info(f"Waiting {STARTUP_DELAY}s for system startup...")
        await asyncio.sleep(STARTUP_DELAY)

        try:
            device_state_sm = messaging.SubMaster(["deviceState"])
        except Exception as e:
            logging.error(f"Failed to initialize deviceState SubMaster: {e}")
            return

        gps_sm = None

        while True:
            try:
                device_state_sm.update(1000)
                current_onroad = device_state_sm['deviceState'].started

                # Handle state transitions
                if current_onroad != self.onroad or gps_sm is None:
                    self.onroad = current_onroad
                    if self.onroad:
                        logging.info("Switching to ONROAD mode.")
                        gps_sm = messaging.SubMaster(["gpsLocation"])
                    else:
                        logging.info("Switching to OFFROAD mode.")
                        gps_sm = None # Don't need GPS SM in offroad if we just ping
                    self.offroad_count = 0

                gps_data = None
                timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

                if self.onroad:
                    gps_sm.update(5000)
                    gps_data = GPSHandler.get_gps_data(gps_sm)
                else:
                    if self.offroad_count % OFFROAD_UPDATE_FACTOR == 0:
                        logging.info("Offroad update ping.")
                        self.offroad_count = 0
                        # gps_data remains None, we'll just send a heartbeat
                    else:
                        self.offroad_count += 1
                        await asyncio.sleep(UPDATE_FREQUENCY)
                        continue

                # Prepare data for sending
                if gps_data:
                    lat, lon, alt, acc, ts, speed, bearing = gps_data
                else:
                    lat, lon, alt, acc, ts, speed, bearing = None, None, None, None, timestamp, None, None

                # Attempt to send
                success = await self.network.send_gps_data(lat, lon, alt, acc, ts, speed, bearing)
                
                if not success:
                    logging.info("Upload failed, buffering data.")
                    self.gps_buffer.append((lat, lon, alt, acc, ts, speed, bearing))
                    if len(self.gps_buffer) >= BUFFER_SIZE:
                        Database.store_gps_data(self.gps_buffer)
                        self.gps_buffer.clear()
                else:
                    # If we succeeded, try to clear the backlog
                    await self.send_stored_data()

                await asyncio.sleep(UPDATE_FREQUENCY)

            except Exception as e:
                logging.error(f"Error in main loop: {e}", exc_info=True)
                await asyncio.sleep(10)

    async def cleanup(self):
        if self.gps_buffer:
            Database.store_gps_data(self.gps_buffer)
        await self.network.close()

if __name__ == "__main__":
    app = GPSTrackerApp()
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        logging.info("Stopping GPS tracker...")
    finally:
        asyncio.run(app.cleanup())
