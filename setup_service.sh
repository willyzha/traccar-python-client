#!/bin/bash

# Variables
SERVICE_NAME="gps-tracker"
SCRIPT_DIR="/data/openpilot/traccar-python-client" # Path to traccar-python-client
LAUNCHER_PATH="$SCRIPT_DIR/launcher.sh"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/gps_tracker.log"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
PYTHON_PATH="/usr/local/pyenv/shims/python3" # Path to the specific Python interpreter

# Ensure the logs directory exists
mkdir -p $LOG_DIR

# Ensure launcher.sh is executable
chmod +x $LAUNCHER_PATH

# Create the systemd service file
echo "Creating systemd service file at $SERVICE_FILE..."

sudo bash -c "cat > $SERVICE_FILE" <<EOL
[Unit]
Description=GPS Tracker Service
After=network.target

[Service]
Type=simple
ExecStartPre=/bin/sleep 60
ExecStart=$PYTHON_PATH $LAUNCHER_PATH
WorkingDirectory=$SCRIPT_DIR
Restart=always
RestartSec=10
StandardOutput=append:$LOG_FILE
StandardError=append:$LOG_FILE
Environment="PYTHONPATH=$PYTHON_PATH"

[Install]
WantedBy=multi-user.target
EOL

# Reload systemd to recognize the new service
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable the service to start on boot
echo "Enabling GPS Tracker service to start on boot..."
sudo systemctl enable $SERVICE_NAME.service

# Start the service now
echo "Starting GPS Tracker service..."
sudo systemctl start $SERVICE_NAME.service

echo "Service setup complete. Logs are located at $LOG_FILE"
