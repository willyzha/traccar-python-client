import cereal.messaging as messaging
import time
from datetime import datetime

# Define the log file path
log_file_path = 'responses.log'

# Function to pretty-print and log messages with a title and content
def pretty_print_and_log(title, content, log_file):
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Pretty print to the console
        print(f"\n========================")
        print(f"{title}")
        print(f"========================")
        print(f"Time: {timestamp}")
        print(f"Content:\n{content}")
        print(f"------------------------\n")

        # Pretty format for logging
        formatted_message = f"""
        =======================
        {title}
        =======================
        Time: {timestamp}
        Content:
        {content}
        -----------------------
        """
        
        # Log to the file
        log_file.write(formatted_message)
        log_file.flush()  # Ensure logs are written immediately
    except Exception as e:
        # If an error occurs, log the error to the log file
        error_message = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - ERROR: Failed to log message. Exception: {str(e)}\n"
        log_file.write(error_message)
        log_file.flush()

# Define the broadcast messages to listen to
broadcasts = [
    'carState',
    'deviceState',
    'ubloxRaw',
    'liveLocationKalman',
    'gpsLocation',
    'gpsLocationExternal'
]

# Set up the SubMaster with the selected broadcasts
try:
    sm = messaging.SubMaster(broadcasts)
except Exception as e:
    with open(log_file_path, 'a') as log_file:
        pretty_print_and_log("ERROR", f"Failed to initialize SubMaster. Exception: {str(e)}", log_file)
    exit(1)  # Exit the script if SubMaster initialization fails

# Open the log file once and keep it open for efficient logging
try:
    with open(log_file_path, 'a') as log_file:
        while True:
            try:
                # Update the messaging data every 5000ms (5 seconds)
                sm.update(5000)
            except Exception as e:
                pretty_print_and_log("ERROR", f"Failed to update SubMaster. Exception: {str(e)}", log_file)
                continue  # Skip this update cycle and continue to the next

            # Loop through the broadcasts dynamically
            for broadcast in broadcasts:
                try:
                    if sm.updated[broadcast]:
                        title = f"Broadcast: {broadcast}"
                        content = str(sm[broadcast])  # Convert content to string for logging and printing
                        pretty_print_and_log(title, content, log_file)
                except KeyError:
                    pretty_print_and_log("ERROR", f"Broadcast '{broadcast}' not found.", log_file)
                except Exception as e:
                    pretty_print_and_log("ERROR", f"Failed to process '{broadcast}'. Exception: {str(e)}", log_file)
            
            # Sleep for 5 seconds before the next update cycle
            time.sleep(5)

except IOError as e:
    # Handle file-related errors like permissions issues or disk full
    print(f"ERROR: Failed to open log file. Exception: {str(e)}")
