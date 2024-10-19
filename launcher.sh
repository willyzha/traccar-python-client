#!/bin/bash

# Get the directory of the current script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Path to the Python script
SCRIPT_PATH="$SCRIPT_DIR/gps_tracker.py"

# Path to the logs directory (relative to the script's location)
LOG_DIR="$SCRIPT_DIR/logs"
LOG_PATH="$LOG_DIR/gps_tracker.log"

# Create logs directory if it doesn't exist
mkdir -p $LOG_DIR

# Activate virtual environment (if using one)
# source $SCRIPT_DIR/venv/bin/activate

# Ensure all dependencies are installed
pip install -r $SCRIPT_DIR/requirements.txt

# Check if the process is already running
if pgrep -f $SCRIPT_PATH > /dev/null
then
    echo "GPS Tracker is already running."
else
    echo "Starting GPS Tracker..."
    
    # Run the Python script in the background with logging
    nohup python3 $SCRIPT_PATH >> $LOG_PATH 2>&1 &
    
    # Ensure the process runs in the background, capture the PID for monitoring
    echo $! > "$SCRIPT_DIR/gps_tracker.pid"
    
    echo "GPS Tracker started in background. Logs are stored in $LOG_PATH."
fi
