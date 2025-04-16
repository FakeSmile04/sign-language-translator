import random
import joblib
import serial
import asyncio
import websockets
from aiohttp import web
import time
import numpy as np
import json
import threading

# Settings
PORT = 8000
WS_PORT = 8765
SERIAL_PORT = 'COM9'
BAUD_RATE = 115200

connected_clients = set()
data_queue = asyncio.Queue()

# --- Serve index.html from /static ---
async def index(request):
    return web.FileResponse('./static/index.html')

def start_http_server():
    app = web.Application()
    app.router.add_get('/', index)
    app.router.add_static('/static/', path='static', name='static')
    web.run_app(app, port=PORT)

# --- WebSocket Handler (v11+ style) ---
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

# Load the pre-trained Random Forest model
model_path = "random_forest_model.pkl"  # Path to your trained model
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
            '''
            features = {
                "MAV": random.randint(0, 100),
                "RMS": random.randint(0, 100),
                "ZC": random.randint(0, 100),
                "WL": random.randint(0, 100),
                "VAR": random.randint(0, 100),
                "IEMG": random.randint(0, 100)
            }
            '''
            features_list = list(features.values())

            # Print features
            #print(f"MAV: {mav:.4f}, RMS: {rms:.4f}, ZC: {zc}, WL: {wl:.4f}, VAR: {var:.4f}, IEMG: {iemg:.4f}")
            # Predict the label using the Random Forest model

            predicted_label = rf_model.predict([features_list])[0]

            # Print the predicted label
            #print(f"Predicted Label: {predicted_label}")
            
            # Create a JSON object with features and predicted label
            to_send = {
                "predicted_label": predicted_label
            }

            asyncio.run_coroutine_threadsafe(queue.put(json.dumps(to_send)), loop)

    except ValueError:
        print("Invalid data format.")

# --- Arduino Serial Reader ---
def read_serial(queue, loop):
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE)
        print(f"Connected to Arduino on {SERIAL_PORT}")
        while True:
            if ser.in_waiting > 0:
                incoming = ser.readline().decode('utf-8').strip()
                try:
                    _, value_str = incoming.split(",")
                    feature_extraction(value_str, queue, loop)
                except Exception:
                    print("Invalid serial format")
    except serial.SerialException as e:
        print(f"Serial error: {e}")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

# --- Boot Everything ---
if __name__ == "__main__":
    # Start the web server
    threading.Thread(target=start_http_server, daemon=True).start()

    # Start WebSocket server and share event loop with serial reader
    loop_ready = threading.Event()
    loop_holder = {}
    threading.Thread(target=start_websocket, args=(loop_holder, loop_ready), daemon=True).start()

    loop_ready.wait()  # Wait until WebSocket loop is ready
    websocket_loop = loop_holder['loop']

    # Start reading Arduino serial data
    read_serial(data_queue, websocket_loop)
