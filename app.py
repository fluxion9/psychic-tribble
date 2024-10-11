from flask import Flask, request, make_response, Response
import cv2
import numpy as np

from detector import detect

app = Flask(__name__)

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
            summary, lvalue = detect(img)
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
            with open("image.jpg", "rb") as f:
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

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)
