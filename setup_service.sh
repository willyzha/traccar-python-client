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

# Check if crontab is available
if ! command -v crontab &>/dev/null; then
    echo "Error: crontab command not found. Please install cron."
    exit 1
fi

# Write a cron job to execute the launcher script on system boot
echo "Setting up cron job to run the GPS Tracker on system boot..."

# Add the cron job to the user's crontab
(
    crontab -l 2>/dev/null | grep -v "@reboot $LAUNCHER_PATH" # Avoid duplicates
    echo "@reboot $LAUNCHER_PATH >> $LOG_FILE 2>&1"
) | crontab -

# Confirm the cron job was added
if crontab -l | grep -q "@reboot $LAUNCHER_PATH"; then
    echo "Cron job setup complete. GPS tracker will run on system boot."
    echo "Logs are located at $LOG_FILE"
else
    echo "Failed to set up the cron job."
fi
