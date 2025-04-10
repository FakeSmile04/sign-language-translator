import random
import serial
from serial import Serial, SerialException
import time
import numpy as np
import json

# Configure the serial connection
arduino_port = 'COM9'  # Replace with your Arduino's port
baud_rate = 115200     # Match the baud rate in your Arduino code

def feature_extraction(data, window_time=3500):
    """
    Perform feature extraction on the incoming data within a specified window time.
    This includes MAV, RMS, ZC, WL, VAR, and IEMG.
    """
    # Static variables to store data and timestamps
    if not hasattr(feature_extraction, "data_buffer"):
        feature_extraction.data_buffer = []
        feature_extraction.timestamp_buffer = []

    try:
        # Convert data to a float and append to buffer
        value = float(data)
        current_time = time.time() * 1000  # Current time in milliseconds
        feature_extraction.data_buffer.append(value)
        feature_extraction.timestamp_buffer.append(current_time)

        # Remove old data outside the window time
        while feature_extraction.timestamp_buffer and current_time - feature_extraction.timestamp_buffer[0] > window_time:
            feature_extraction.data_buffer.pop(0)
            feature_extraction.timestamp_buffer.pop(0)

        # Perform feature extraction if we have enough data
        if len(feature_extraction.data_buffer) > 1:
            buffer = np.array(feature_extraction.data_buffer)
            
            # Calculate features
            mav = np.mean(np.abs(buffer))
            rms = np.sqrt(np.mean(buffer**2))
            zc = np.sum(np.diff(np.sign(buffer)) != 0)
            wl = np.sum(np.abs(np.diff(buffer)))
            var = np.var(buffer)
            iemg = np.sum(np.abs(buffer))
            '''
            # Calculate features placeholder
            mav = random.randint(0, 100)
            rms = random.randint(0, 100) 
            zc = random.randint(0, 100) 
            wl = random.randint(0, 100) 
            var = random.randint(0, 100) 
            iemg = random.randint(0, 100) 
            '''
            features = {
                "MAV": mav,
                "RMS": rms,
                "ZC": zc,
                "WL": wl,
                "VAR": var,
                "IEMG": iemg
            }
            
            # Print features
            print(f"MAV: {mav:.4f}, RMS: {rms:.4f}, ZC: {zc}, WL: {wl:.4f}, VAR: {var:.4f}, IEMG: {iemg:.4f}")

            # Send features to the server
            send_features_to_server(features)

    except ValueError:
        print("Invalid data format.")

import requests  # Import requests for sending data to the web server

def send_features_to_server(features):
    """
    Send the extracted features to a web server.
    
    :param features: A dictionary containing the extracted features.
    """

    # Convert numpy types to standard Python types
    features = {key: (value.item() if isinstance(value, (np.int32, np.float32, np.int64, np.float64)) else value)
                for key, value in features.items()}
    
    json_string = json.dumps(features)

    # Placeholder URL for the web server
    #web_server_url = 'https://docs.google.com/forms/d/e/1FAIpQLScrI6nQfNtojhPeIMcyFgMmPGBuGTNFdhh3XKgHlPRWEc49_Q/formResponse?.entry.416040466='+json_string
    web_server_url = 'http://localhost/homepage.php'  # Replace with your web server URL
    
    try:
        # Send the POST request
        response = requests.post(web_server_url, json=features)
        if response.status_code == 200:
            print("Features successfully sent to the server.")
        else:
            print(f"Failed to send features. Status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending features to server: {e}")

try:
    # Establish the connection
    ser = Serial(arduino_port, baud_rate)
    print(f"Connected to Arduino on port {arduino_port}")

    while True:
        if ser.in_waiting > 0:
            # Read incoming data from Arduino
            incoming_data = ser.readline().decode('utf-8').strip()
            #print(f"Raw Data: {incoming_data}")
            
            # Ensure the data is in the format "time, value"
            try:
                time_str, value_str = incoming_data.split(",")
                value = float(value_str)  # Extract the value as a float
            except (ValueError, IndexError):
                print("Invalid data format. Skipping...")
                continue

            # Perform feature extraction on the extracted value
            feature_extraction(value)

except SerialException as e:
    print(f"Error: {e}")

except KeyboardInterrupt:
    print("\nExiting program.")

finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()
        print("Serial connection closed.")
