import cv2
import websockets
import asyncio

# Set the IP address and port of the WebSocket server
# server_ip = "ws://localhost:3001"
server_ip = "ws://134.122.88.128:3001"
# server_ip = "ws://209.38.181.224:3001"

async def send_frame(websocket, frame):
    # Encode the frame as JPEG
    _, buffer = cv2.imencode('.jpg', frame)
    # Send the raw byte data to the WebSocket server
    await websocket.send(buffer.tobytes())
    response = await websocket.recv()
    print(f"Server response: {response}")

async def stream_video():
    # Connect to the WebSocket server
    async with websockets.connect(server_ip) as websocket:
        # Open the webcam (use 0 for the default webcam)
        cap = cv2.VideoCapture(0)
        print("Streaming.....")
        try:
            while True:
                # Capture frame-by-frame
                ret, frame = cap.read()
                if not ret:
                    print("Failed to capture frame")
                    break
                # Send the frame to the WebSocket server
                await send_frame(websocket, frame)
        finally:
            cap.release()
# Run the async loop to stream video
asyncio.get_event_loop().run_until_complete(stream_video())
