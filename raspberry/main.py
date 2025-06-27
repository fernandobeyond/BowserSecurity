# En Raspberry Pi: Transmisión MJPEG por Flask
from flask import Flask, Response
from picamera2 import Picamera2
import cv2, time

app = Flask(__name__)
picam2 = Picamera2()
config = picam2.create_video_configuration(main={"format": "YUV420", "size": (640, 360)})
picam2.configure(config)
picam2.start()
time.sleep(1)

def generate():
    while True:
        frame = picam2.capture_array("main")
        frame = cv2.cvtColor(frame, cv2.COLOR_YUV2BGR_I420)
        _, jpeg = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')

@app.route('/video')
def video_feed():
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

app.run(host="0.0.0.0", port=8080)
