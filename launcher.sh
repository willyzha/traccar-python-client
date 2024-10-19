#!/bin/bash

# Define the working directory for the GPS tracker
SCRIPT_DIR="/data/openpilot/traccar-python-client"
OPENPILOT_DIR="/data/openpilot"  # The directory where the OpenPilot code is located

# Path to the Python script
SCRIPT_PATH="$SCRIPT_DIR/gps_tracker.py"

# Activate virtual environment (if using one)
# source $SCRIPT_DIR/venv/bin/activate

# Add openpilot directory to PYTHONPATH so that the script can find the 'cereal' package
export PYTHONPATH="$OPENPILOT_DIR:$PYTHONPATH"

# Ensure all dependencies are installed
pip install -r $SCRIPT_DIR/requirements.txt

# Check if the process is already running
if pgrep -f $SCRIPT_PATH > /dev/null
then
    echo "GPS Tracker is already running."
else
    echo "Starting GPS Tracker..."
    # Run the Python script (logging will be handled by systemd)
    python3 $SCRIPT_PATH
    echo "GPS Tracker started."
fi
