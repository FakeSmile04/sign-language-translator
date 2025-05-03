import random
import joblib
import asyncio
import websockets
from aiohttp import web
import time
import numpy as np
import json
import threading
import paho.mqtt.client as mqtt
import os

# Settings
PORT = 8000
WS_PORT = 8765
MQTT_BROKER = "broker.hivemq.com" # Replace with your MQTT broker address
MQTT_TOPIC = "esp32/emg"  # Replace with your MQTT topic

connected_clients = set()
data_queue = asyncio.Queue()

# --- Serve index.html from /static ---
async def index(request):
    print("Serving index.html")  # Debug
    return web.FileResponse('./static/index.html')

# In app.py, modify the start_http_server function:
def start_http_server():
    app = web.Application()
    
    # Get absolute path to static folder
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    static_path = os.path.join(current_dir, 'static')
    
    # Verify index.html exists
    if not os.path.exists(os.path.join(static_path, 'index.html')):
        print(f"Error: index.html not found at {static_path}")
        exit(1)
    
    app.router.add_get('/', lambda r: web.FileResponse(os.path.join(static_path, 'index.html')))
    app.router.add_static('/static/', path=static_path)
    
    print(f"Serving from {static_path}")
    web.run_app(app, port=PORT)

# --- WebSocket Handler ---
async def ws_handler(websocket):
    connected_clients.add(websocket)
    print("Client connected")
    try:
        while True:
            await asyncio.sleep(1)  # Keep connection alive
    except websockets.exceptions.ConnectionClosed as e:
        print(f"Client disconnected: {e.code} - {e.reason}")
    finally:
        connected_clients.remove(websocket)

# --- Combined WebSocket Server + Sender Loop ---
def start_websocket(loop_holder, ready_event):
    async def run():
        async with websockets.serve(ws_handler, "0.0.0.0", WS_PORT):
            print(f"WebSocket server running at ws://127.0.0.1:{WS_PORT}")
            loop_holder['loop'] = asyncio.get_running_loop()
            ready_event.set()

            try:
                while True:
                    data = await data_queue.get()
                    if connected_clients:
                        tasks = [asyncio.create_task(client.send(data)) for client in connected_clients]
                        await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as e:
                print("WebSocket sender loop error:", e)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run())

# --- MQTT Callbacks ---
def on_connect(client, userdata, flags, reason_code, properties):  # Updated for v2
    if reason_code == 0:
        print("Connected to MQTT Broker!")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"Failed to connect, reason code: {reason_code}")

def on_message(client, userdata, msg):
    try:
        # First, clean the payload by removing null bytes
        clean_payload = msg.payload.decode('utf-8').split('\x00')[0]
        
        if clean_payload:  # Only process if we got actual data
            try:
                data = json.loads(clean_payload)
                value = data["value"]
                feature_extraction(str(value), data_queue, userdata['loop'])
                #print(f"Received JSON data.")
            except json.JSONDecodeError:
                print(f"Received non-JSON data: {clean_payload}")
            except KeyError:
                print(f"JSON missing 'value' key: {clean_payload}")
    except Exception as e:
        print(f"Error processing message: {e}")

# Load the pre-trained Random Forest model
model_path = os.path.join(os.path.dirname(__file__), "random_forest_model.pkl")
try:
    rf_model = joblib.load(model_path)
    print("Random Forest model loaded successfully.")
except FileNotFoundError:
    print(f"Error: Model file '{model_path}' not found.")
    exit()

labels = ["peace", "rock", "thumbs"]

# --- Feature Extraction Logic ---
def feature_extraction(data, queue, loop):
    if not hasattr(feature_extraction, "data_buffer"):
        feature_extraction.data_buffer = []
        feature_extraction.timestamp_buffer = []

    try:
        value = float(data)
        current_time = time.time() * 1000
        feature_extraction.data_buffer.append(value)
        feature_extraction.timestamp_buffer.append(current_time)

        while feature_extraction.timestamp_buffer and current_time - feature_extraction.timestamp_buffer[0] > 3500:
            feature_extraction.data_buffer.pop(0)
            feature_extraction.timestamp_buffer.pop(0)

        if len(feature_extraction.data_buffer) > 1:
            buffer = np.array(feature_extraction.data_buffer)
            
            features = {
                "MAV": np.mean(np.abs(buffer)),
                "RMS": np.sqrt(np.mean(buffer**2)),
                "ZC": int(np.sum(np.diff(np.sign(buffer)) != 0)),
                "WL": float(np.sum(np.abs(np.diff(buffer)))),
                "VAR": float(np.var(buffer)),
                "IEMG": float(np.sum(np.abs(buffer)))
            }

            features_list = list(features.values())
            predicted_label = rf_model.predict([features_list])[0]
            
            to_send = {
                "predicted_label": predicted_label
            }

            asyncio.run_coroutine_threadsafe(queue.put(json.dumps(to_send)), loop)

    except ValueError:
        print("Invalid data format.")

# --- Start MQTT Client ---
def start_mqtt_client(loop):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.user_data_set({'loop': loop})
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, 1883, 60)
        client.loop_forever()
    except Exception as e:
        print(f"MQTT connection error: {e}")

# --- Boot Everything ---
if __name__ == "__main__":
    # Start the web server
    threading.Thread(target=start_http_server, daemon=True).start()

    # Start WebSocket server and share event loop with MQTT client
    loop_ready = threading.Event()
    loop_holder = {}
    threading.Thread(target=start_websocket, args=(loop_holder, loop_ready), daemon=True).start()

    loop_ready.wait()  # Wait until WebSocket loop is ready
    websocket_loop = loop_holder['loop']

    # Start MQTT client
    start_mqtt_client(websocket_loop)