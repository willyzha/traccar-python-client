#!/bin/bash

# Variables
SERVICE_NAME="gps-tracker"
SCRIPT_DIR="/data/openpilot/traccar-python-client" # Path to traccar-python-client
LAUNCHER_PATH="$SCRIPT_DIR/launcher.sh"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/gps_tracker.log"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
LAST_TARGET_FILE="/etc/systemd/system/last.target"
PYTHON_PATH="/usr/local/pyenv/shims/python3" # Path to the specific Python interpreter

# Ensure the logs directory exists
mkdir -p $LOG_DIR

# Ensure launcher.sh is executable
chmod +x $LAUNCHER_PATH

# Create the last.target file to ensure this service starts last
echo "Creating last target file at $LAST_TARGET_FILE..."
sudo bash -c "cat > $LAST_TARGET_FILE" <<EOL
[Unit]
Description=Last Target
Requires=multi-user.target
After=multi-user.target
EOL

# Create the systemd service file
echo "Creating systemd service file at $SERVICE_FILE..."

sudo bash -c "cat > $SERVICE_FILE" <<EOL
[Unit]
Description=GPS Tracker Service
After=last.target
Wants=last.target

[Service]
Type=simple
ExecStart=/bin/bash $LAUNCHER_PATH
WorkingDirectory=$SCRIPT_DIR
Restart=always
RestartSec=10
StandardOutput=append:$LOG_FILE
StandardError=append:$LOG_FILE
Environment="PYTHONPATH=$PYTHON_PATH"

[Install]
WantedBy=multi-user.target
EOL

# Reload systemd to recognize the new files
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable both last.target and the GPS Tracker service
echo "Enabling last target and GPS Tracker service to start at the end of the boot process..."
sudo systemctl enable last.target
sudo systemctl enable $SERVICE_NAME.service

# Start the service now
echo "Starting GPS Tracker service..."
sudo systemctl start $SERVICE_NAME.service

echo "Service setup complete. Logs are located at $LOG_FILE"
