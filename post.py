import cv2
import requests
import time


def upload_image(image_data):
    url = 'http://localhost:5000/send'
    response = requests.post(url, files={'file': ('image.jpg', image_data, 'image/jpeg')})
    print(response.text)

def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Failed to open webcam")
        return
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture image")
            break
        _,jpeg = cv2.imencode('.jpg', frame)
        jpeg = jpeg.tobytes()
        if jpeg:
            upload_image(jpeg)
        # time.sleep(1)
    cap.release()

if __name__ == "__main__":
    main()
