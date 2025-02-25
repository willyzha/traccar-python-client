#!/bin/bash

# Variables
SERVICE_NAME="gps-tracker"
SCRIPT_DIR="/persist/traccar-python-client" # Path to traccar-python-client
LAUNCHER_PATH="$SCRIPT_DIR/launcher.sh"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
PYTHON_PATH="/usr/local/pyenv/shims/python3" # Path to the specific Python interpreter

# Ensure launcher.sh is executable
chmod +x $LAUNCHER_PATH

# Ensure all dependencies are installed using the correct Python interpreter
$PYTHON_PATH -m pip install -r $SCRIPT_DIR/requirements.txt

# Create the systemd service file with simplified dependencies
echo "Creating systemd service file at $SERVICE_FILE..."

sudo bash -c "cat > $SERVICE_FILE" <<EOL
[Unit]
Description=GPS Tracker Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStartPre=/bin/sleep 10
ExecStart=/bin/bash /persist/traccar-python-client/launcher.sh
WorkingDirectory=/persist/traccar-python-client
Restart=always
RestartSec=10
StartLimitInterval=200
StartLimitBurst=5
Environment="PYTHONPATH=/usr/local/pyenv/shims/python3"

[Install]
WantedBy=multi-user.target
EOL

# Reload systemd to recognize the new files
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable the GPS Tracker service
echo "Enabling GPS Tracker service to start after network-online.target..."
sudo systemctl enable $SERVICE_NAME.service

echo "Service setup complete. Logs are located at $LOG_FILE"
