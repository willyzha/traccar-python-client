Comma 3x Traccar Python Client
==============================

A lightweight, high-performance GPS tracking client designed for Comma 3x devices, enabling efficient and reliable data management with Traccar.

Features
--------

- **Asynchronous I/O:** Uses `asyncio` and `httpx` for non-blocking network operations, ensuring the tracking loop remains responsive.
- **Persistent Connections:** Maintains an active HTTP session for efficient data transmission.
- **Robust Local Storage:** Uses SQLite with transaction-safe context managers to buffer data when offline.
- **Smart Power Management:** Automatically switches between Onroad (high frequency) and Offroad (heartbeat) modes.
- **Graceful Transitions:** Seamlessly handles device state changes without requiring script restarts.
- **Modern Python:** Fully type-hinted and uses UTC-aware timestamps.

Quick Setup on Comma 3x
-----------------------

### Clone the Repository:

    git clone https://github.com/webnizam/traccar-python-client
    cd traccar-python-client
    

### Configuration:

1. Copy the example environment file:
   `cp .env.example .env`
2. Edit `.env` to set your `SERVER_URL` and `DEVICE_ID`.

### Run the Setup Script:

    sudo ./setup_service.sh
    

**Note:** The setup script automatically handles the installation of all necessary Python dependencies (like `httpx` and `python-decouple`) using the device's internal Python interpreter. You do not need to run `pip install` manually unless you are troubleshooting.

### Manual Dependency Installation (Optional):

If you ever need to manually install or update dependencies on the device:

    /usr/local/pyenv/shims/python3 -m pip install -r requirements.txt

Configuration (.env)
-------------

- `SERVER_URL`: Your Traccar server URL (e.g., `https://demo.traccar.org`).
- `SERVER_PORT`: (Optional) The port for the OsmAnd protocol (usually `5055`).
- `DEVICE_ID`: Your unique device identifier.
- `UPDATE_FREQUENCY`: Seconds between updates while Onroad.
- `OFFROAD_UPDATE_FACTOR`: Multiply `UPDATE_FREQUENCY` by this for Offroad heartbeats.
- `DB_PATH`: Path to the local SQLite database.
- `BUFFER_SIZE`: Number of records to buffer in memory before flushing to disk.
- `STARTUP_DELAY`: Seconds to wait after boot before starting the tracker.

Monitoring
----------

Check service status:
`systemctl status gps-tracker.service`

View logs:
`journalctl -u gps-tracker.service -f`
