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
import pandas as pd
from collections import deque
from threading import Lock


# Settings
PORT = 8000
WS_PORT = 8765
MQTT_BROKER = "192.168.43.242" # Replace with your MQTT broker address
TOPIC = "esp32/emg"  # Replace with your MQTT topic
MAIN_WINDOW_MS = 4000        # 4-second buffer
SUB_WINDOW_MS = 500          # 500 ms subwindow
OVERLAP_MS = 250             # 250 ms overlap
SAMPLE_RATE = 100            # approx samples per second
buffer = []

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
    async def sender():
        while True:
            data = await data_queue.get()
            if connected_clients:
                print(f"📤 Sending to {len(connected_clients)} client(s): {data}")
                tasks = [asyncio.create_task(client.send(data)) for client in connected_clients]
                await asyncio.gather(*tasks, return_exceptions=True)

    async def run():
        async with websockets.serve(ws_handler, "0.0.0.0", WS_PORT):
            print(f"✅ WebSocket server running at ws://127.0.0.1:{WS_PORT}")
            loop_holder['loop'] = asyncio.get_running_loop()
            ready_event.set()

            # Start sender loop in background
            asyncio.create_task(sender())

            # Keep the server alive
            while True:
                await asyncio.sleep(3600)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run())

# --- MQTT Callbacks ---
def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected with result code {reason_code}")
    client.subscribe(TOPIC)

last_prediction_time = 0  # track sliding interval

def on_message(client, userdata, msg):
    global buffer, last_prediction_time
    loop = userdata['loop']

    try:
        payload = msg.payload.decode().strip()
        payload = payload.replace("{", "").replace("}", "")
        values = [float(x) for x in payload.split(",")]

        if len(values) != 9:
            return

        timestamp, emg1, emg2, accx, accy, accz, gyrox, gyroy, gyroz = values
        buffer.append([timestamp, emg1, emg2, accx, accy, accz, gyrox, gyroy, gyroz])

        # Keep only data from the last WINDOW_MS milliseconds
        min_time = timestamp - MAIN_WINDOW_MS
        buffer = [row for row in buffer if row[0] >= min_time]

        # Run prediction every OVERLAP_MS
        if timestamp - last_prediction_time >= OVERLAP_MS:
            df = pd.DataFrame(buffer, columns=["time","emg1","emg2","accx","accy","accz","gyrox","gyroy","gyroz"])
            df_window = df[df["time"] >= (timestamp - SUB_WINDOW_MS)]
            if len(df_window) == 0:
                return

            feats = feature_extraction(df_window)
            if len(feats.columns) == 0:
                return

            # Get probabilities for each class
            probs = model.predict_proba(feats.to_numpy())[0]
            max_prob_index = np.argmax(probs)
            max_prob = probs[max_prob_index]

            if max_prob >= 0.4:
                pred = model.classes_[max_prob_index]
                #print(pred)
                to_send = {"predicted_label": pred}
                asyncio.run_coroutine_threadsafe(data_queue.put(json.dumps(to_send)), loop)
                print(f"🖐 Predicted: {pred} ({max_prob*100:.1f}% confidence)")
            else:
                print("❌ Not recognized (confidence below 50%)")

            last_prediction_time = timestamp

    except Exception as e:
        print("Error:", e)

# Load the pre-trained Random Forest model
#model_path = os.path.join(os.path.dirname(__file__), r"EMG FINAL\sign-language-translator\websocket_page\random_forest_model_windows.pkl")
try:
    model = joblib.load(r"EMG FINAL\sign-language-translator\websocket_page\random_forest_model_windows.pkl")
    print("Random Forest model loaded successfully.")
except FileNotFoundError:
    print(f"Error: Model file '{model}' not found.")
    exit()

labels = ["thank","help","welcome"]

# --- Feature Extraction Logic ---
def feature_extraction(df_window):
    """Compute same features used during training"""
    feats = {}
    sensors = ["emg1", "emg2", "accx", "accy", "accz", "gyrox", "gyroy", "gyroz"]
    for s in sensors:
        data = df_window[s].values
        if len(data) == 0:
            continue
        feats[f"{s}_mav"] = np.mean(np.abs(data))
        feats[f"{s}_rms"] = np.sqrt(np.mean(np.square(data)))
        feats[f"{s}_var"] = np.var(data)
        feats[f"{s}_zc"] = np.sum(np.diff(np.sign(data)) != 0)
        feats[f"{s}_wl"] = np.sum(np.abs(np.diff(data)))
        feats[f"{s}_iemg"] = np.sum(np.abs(data))
    return pd.DataFrame([feats])

def process_buffer(df):
    """Split 4s buffer into 500ms subwindows with 250ms overlap and predict."""
    start = df["time"].min()
    end = df["time"].max()

    current_start = start
    while current_start + SUB_WINDOW_MS <= end:
        current_end = current_start + SUB_WINDOW_MS
        df_window = df[(df["time"] >= current_start) & (df["time"] < current_end)]

        if len(df_window) > 0:
            feats = feature_extraction(df_window)
            print("Extracted features:", feats)
            if len(feats.columns) > 0:
                pred = model.predict(feats.to_numpy())[0]
                print(f"🖐 Predicted gesture ({current_start:.0f}-{current_end:.0f} ms): {pred}")

        current_start += (SUB_WINDOW_MS - OVERLAP_MS)

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