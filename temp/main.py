import asyncio
import websockets
import cv2
import numpy as np
from flask import Flask, Response
import threading

from detector import detect

# Flask app initialization
app = Flask(__name__)

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
                    summary, lvalue = detect(img)
                    person = summary.__contains__('person')
                    dark = lvalue <= 13.0
                    response = {'person': person, 'dark': dark}
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
            with open("temp/image.jpg", "rb") as f:
                image_bytes = f.read()
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise Exception
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + image_bytes + b'\r\n')
        except Exception as e:
            # print(f"Exception: {e}")
            with open("blind.jpg", "rb") as f:
                image_bytes = f.read()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + image_bytes + b'\r\n')
            continue
# Function to start the Flask app
def start_flask_app():
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)

# Start both WebSocket and Flask servers concurrently
def run_servers():
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=start_flask_app)
    flask_thread.start()

    # Start WebSocket server in the main asyncio loop
    asyncio.run(start_websocket_server())

if __name__ == "__main__":
    run_servers()
