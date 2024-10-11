from flask import Flask, request, make_response, Response
import cv2
import numpy as np

from detector import detect

app = Flask(__name__)

with open("blind.jpg", "rb") as f:
    blind_buffer = f.read()

image_buffer = None

@app.route('/')
def index():
    return make_response('Hello there!', 200)

@app.route('/send', methods=['POST'])
def send_file():
    if 'file' not in request.files:
        return make_response('', 400)
    file = request.files['file']
    if file.filename == '':
        return make_response('', 400)
    if file:
        image_data = file.read()
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is not None:
            global image_buffer
            summary, lvalue, image_buffer = detect(img)
            person = 'person' in summary
            dark = lvalue <= 13.0
            response = {'person': person, 'dark': dark}
            return make_response(str(response), 200)
        else:
            return make_response('', 400)

@app.route('/live')
def stream():
    return Response(get_frame(), mimetype='multipart/x-mixed-replace; boundary=frame')


def get_frame():
    while True:
        try:
            if image_buffer is None:
                raise Exception
            success, enc = cv2.imencode('.jpg', image_buffer)
            if success:
                image_bytes = enc.tobytes()
            else:
                print("Failed to encode image")
                raise Exception
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + image_bytes + b'\r\n')
        except Exception as e:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + blind_buffer + b'\r\n')
            continue

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)
