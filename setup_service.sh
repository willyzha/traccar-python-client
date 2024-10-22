#!/bin/bash

# Variables
SERVICE_NAME="gps-tracker"
SCRIPT_DIR="/data/openpilot/traccar-python-client" # Path to traccar-python-client
LAUNCHER_PATH="$SCRIPT_DIR/launcher.sh"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/gps_tracker.log"

# Ensure the logs directory exists
mkdir -p $LOG_DIR

# Ensure launcher.sh is executable
chmod +x $LAUNCHER_PATH

# Write a cron job to execute the launcher script on system boot
echo "Setting up cron job to run the GPS Tracker on system boot..."

# Add the cron job (this will append the cron job to the user's crontab)
(
    crontab -l 2>/dev/null
    echo "@reboot $LAUNCHER_PATH >> $LOG_FILE 2>&1"
) | crontab -

echo "Cron job setup complete. GPS tracker will run on system boot. Logs are located at $LOG_FILE"
