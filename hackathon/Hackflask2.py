from flask import Flask, render_template, Response
import cv2
import mediapipe as mp
import threading
import time
import pyaudio
import numpy as np
import pygetwindow as gw
import platform
import subprocess

app = Flask(__name__)

# Mediapipe setup
mp_face_detection = mp.solutions.face_detection
mp_drawing = mp.solutions.drawing_utils

# Constants
TAB_CHECK_INTERVAL = 2
HEAD_SHIFT_THRESHOLD = 20
NO_FACE_THRESHOLD = 30
NO_OF_FACES_THRESHOLD = 1
VOICE_THRESHOLD = 5000

# Global variables
alerts = {}  # Change from list to dictionary
prev_face_coords = None
no_face_counter = 0

def add_alert(message):
    """Adds an alert or increments the count if the alert already exists."""
    if message in alerts:
        alerts[message] += 1
    else:
        alerts[message] = 1

def monitor_tab_switching():
    previous_window = gw.getActiveWindow().title if gw.getActiveWindow() else None
    while True:
        current_window = gw.getActiveWindow()
        if current_window and current_window.title != previous_window:
            add_alert("Tab switching detected!")
            print("Alert added: Tab switching detected!")  # Debugging
            previous_window = current_window.title
        time.sleep(TAB_CHECK_INTERVAL)

def detect_face_shifts_and_multiple_faces(frame, face_detection):
    global prev_face_coords, no_face_counter

    results = face_detection.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    if results.detections:
        no_face_counter = 0
        face_count = len(results.detections)

        if face_count > NO_OF_FACES_THRESHOLD:
            add_alert(f"Multiple faces detected: {face_count}!")

        detection = results.detections[0]
        bboxC = detection.location_data.relative_bounding_box
        h, w, _ = frame.shape
        current_coords = (
            int(bboxC.xmin * w),
            int(bboxC.ymin * h),
            int(bboxC.width * w),
            int(bboxC.height * h),
        )

        if prev_face_coords:
            shift_distance = ((prev_face_coords[0] - current_coords[0]) ** 2 + (prev_face_coords[1] - current_coords[1]) ** 2) ** 0.5
            if shift_distance > HEAD_SHIFT_THRESHOLD:
                add_alert("Face shift detected!")

        prev_face_coords = current_coords
    else:
        no_face_counter += 1
        if no_face_counter >= NO_FACE_THRESHOLD:
            add_alert("No face detected!")
            time.sleep(20)

def monitor_sound_levels():
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=44100,
        input=True,
        frames_per_buffer=1024,
    )

    while True:
        data = stream.read(1024, exception_on_overflow=False)
        audio_data = np.frombuffer(data, dtype=np.int16)
        volume = np.linalg.norm(audio_data)

        if volume > VOICE_THRESHOLD:
            add_alert("Loud noise detected!")
            time.sleep(15)

def detect_vm_environment():
    vm_indicators = ["VirtualBox", "VMware", "Hyper-V", "QEMU", "Parallels"]
    try:
        if platform.system() == "Windows":
            bios_info = subprocess.check_output("wmic bios get smbiosbiosversion", shell=True).decode()
        else:
            bios_info = subprocess.check_output("dmidecode -s bios-version", shell=True).decode()

        for indicator in vm_indicators:
            if indicator.lower() in bios_info.lower():
                add_alert(f"Virtual Machine detected ({indicator})!")
                break
    except Exception as e: 
        add_alert(f"Error detecting VM environment: {e}")
@app.route('/get_alerts')
def get_alerts():
    alert_data = [{'message': alert, 'count': count} for alert, count in alerts.items()]
    return jsonify({'alerts': alert_data})



# @app.route('/')
# def index():
#     return render_template('index.html', alerts=alerts)


def generate_video_feed():
    cap = cv2.VideoCapture(0)
    with mp_face_detection.FaceDetection(min_detection_confidence=0.7) as face_detection:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            detect_face_shifts_and_multiple_faces(frame, face_detection)

            _, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    cap.release()

@app.route('/video_feed')
def video_feed():
    return Response(generate_video_feed(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    threading.Thread(target=monitor_tab_switching, daemon=True).start()
    threading.Thread(target=monitor_sound_levels, daemon=True).start()
    detect_vm_environment()
    app.run(debug=True, host='0.0.0.0')
