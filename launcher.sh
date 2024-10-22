#!/bin/bash

# Define the working directory for the GPS tracker
SCRIPT_DIR="/data/openpilot/traccar-python-client"
OPENPILOT_DIR="/data/openpilot" # The directory where the OpenPilot code is located

# Path to the Python script
SCRIPT_PATH="$SCRIPT_DIR/gps_tracker.py"

# Specify the Python path
PYTHON_PATH="/usr/local/pyenv/shims/python3"

# Ensure all dependencies are installed using the correct Python interpreter
$PYTHON_PATH -m pip install -r $SCRIPT_DIR/requirements.txt

# Check if the process is already running
if pgrep -f $SCRIPT_PATH >/dev/null; then
    echo "GPS Tracker is already running."
else
    echo "Starting GPS Tracker..."
    # Run the Python script with the specified Python interpreter
    $PYTHON_PATH $SCRIPT_PATH
    echo "GPS Tracker started."
fi
