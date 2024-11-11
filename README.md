Comma 3x Traccar Python Client
==============================

A lightweight GPS tracking client designed for easy integration with Comma 3x, enabling efficient and reliable data management.

Quick Setup on Comma 3x
-----------------------

### Clone the Repository:

    git clone https://github.com/webnizam/traccar-python-client
    cd traccar-python-client
    

### Run the Setup Script:

    sudo ./setup_service.sh
    

This will configure and enable the application as a system service on your Comma 3x.

Configuration
-------------

**.env File:** Edit the `.env` file to customize settings like port numbers and other environment variables as needed for your setup.

Running the GPS Tracker
-----------------------

The application runs as a background service, managed via `launcher.sh`. This ensures the GPS tracker starts automatically with the device and stays active.

Logs and Monitoring
-------------------

Application logs are stored in the `logs` directory, providing easy access for monitoring and troubleshooting.

Dependencies
------------

Ensure all Python dependencies are installed:

    pip install -r requirements.txt
    
### Setup Instructions

    sudo mount -o remount,rw /persist
    cd /persist
    git clone https://github.com/webnizam/traccar-python-client

    # Edit and config .env as required

    sudo mount -o remount,rw /
    sudo bash setup_service.sh
    
    # Reboot and test
    sudo reboot
    systemctl status gps-tracker.service

Contributions & Support
-----------------------

We welcome contributions! Feel free to submit issues or pull requests on the GitHub page. For any questions or support, refer to the repository's issues section.