#!/bin/bash

# Define the working directory for the GPS tracker
SCRIPT_DIR="/persist/traccar-python-client"
OPENPILOT_DIR="/data/openpilot" # The directory where the OpenPilot code is located

# Path to the Python script
SCRIPT_PATH="$SCRIPT_DIR/gps_tracker.py"

# Specify the Python path
PYTHON_PATH="/usr/local/pyenv/shims/python3"

# Add OpenPilot directory to PYTHONPATH so that the script can find the 'cereal' package
export PYTHONPATH="$OPENPILOT_DIR:$PYTHONPATH"

# Check if the process is already running
if pgrep -f $SCRIPT_PATH >/dev/null; then
    echo "GPS Tracker is already running."
else
    echo "Starting GPS Tracker..."
    # Run the Python script with the specified Python interpreter
    $PYTHON_PATH $SCRIPT_PATH
    echo "GPS Tracker started."
fi
