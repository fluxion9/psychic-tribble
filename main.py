import asyncio
import websockets
import cv2
import numpy as np
from flask import Flask, Response
import threading
import sys
import logging

from detector import detect

class LoggerWriter:
    def __init__(self, level):
        self.level = level

    def write(self, message):
        if message != '\n':
            self.level(message)

    def flush(self):
        pass

# Configure the logging
logging.basicConfig(filename='proc.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logger = logging.getLogger()

sys.stdout = LoggerWriter(logger.info)
sys.stderr = LoggerWriter(logger.error)

# Flask app initialization
app = Flask(__name__)

with open("blind.jpg", "rb") as f:
    blind_buffer = f.read()

image_buffer = None

# WebSocket handler to receive image data and process with OpenCV
async def handle_connection(websocket, path):
    while True:
        try:
            # Receive image data from WebSocket
            message = await websocket.recv()
            if len(message) > 5000:  # Check for large enough message to be an image
                # Convert the image bytes to an OpenCV image
                nparr = np.frombuffer(message, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if img is not None:
                    global image_buffer
                    summary, lvalue, image_buffer = detect(img)
                    person = summary.__contains__('person')
                    dark = lvalue <= 13.0
                    # response = {'person': person, 'dark': dark}
                    response = [int(person), int(dark), round(lvalue, 1)]
                    # print(response)
                    await websocket.send(str(response))
        except websockets.exceptions.ConnectionClosed:
            break

# WebSocket server initialization
async def start_websocket_server():
    server = await websockets.serve(handle_connection, '0.0.0.0', 3001)
    await server.wait_closed()

@app.route('/')
def index():
    return 'Hello!'

# Flask route to serve the image as a live stream
@app.route('/live')
def stream():
    return Response(get_image(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Function to retrieve and stream the image
def get_image():
    while True:
        try:
            if image_buffer is None:
                raise Exception
            success, enc = cv2.imencode('.jpg', image_buffer)
            if success:
                image_bytes = enc.tobytes()
            else:
                raise Exception
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + image_bytes + b'\r\n')
        except Exception as e:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + blind_buffer + b'\r\n')
            continue
# Function to start the Flask app
def start_flask_app():
    app.run(host='0.0.0.0', port=4045, debug=False, threaded=True)

# Start both WebSocket and Flask servers concurrently
def run_servers():
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=start_flask_app)
    flask_thread.start()

    # Start WebSocket server in the main asyncio loop
    asyncio.run(start_websocket_server())

if __name__ == "__main__":
    run_servers()
