from flask import Flask, render_template, Response, jsonify
import cv2
import mediapipe as mp
import threading
import time
import pyaudio
import numpy as np
import pygetwindow as gw
import platform
import subprocess
from threading import Lock


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

COOLDOWN_SECONDS = 3  # Reduced cooldown to 3 seconds

# Last alert timestamp
last_sound_alert = 0

# Global variables
alerts = {}  # Dictionary to store alerts
alert_lock = Lock()  # Ensure thread safety
prev_face_coords = None
no_face_counter = 0
last_error = None

LAST_ALERT_TIME = {"face_shift": 0, "multiple_faces": 0, "no_face": 0, "tab_switch": 0}

COOLDOWN_SECONDS = 1


def add_alert(message):
    """Adds an alert or increments the count if the alert already exists."""
    with alert_lock:
        if message in alerts:
            alerts[message] += 1
        else:
            alerts[message] = 1


def monitor_tab_switching():
    COOLDOWN_SECONDS = 1
    """Monitors for tab/window switching."""
    previous_window = gw.getActiveWindow().title if gw.getActiveWindow() else None

    while True:
        current_window = gw.getActiveWindow()
        current_time = time.time()

        if current_window and current_window.title != previous_window:
            if current_time - LAST_ALERT_TIME["tab_switch"] > COOLDOWN_SECONDS:
                add_alert("Tab switching detected!")
                LAST_ALERT_TIME["tab_switch"] = (
                    current_time  # Update last alert timestamp
                )

            previous_window = current_window.title  # Update previous window

        time.sleep(0.01)  # Small delay to reduce CPU usage


def detect_face_shifts_and_multiple_faces(frame, face_detection):
    """Detects face shifts, multiple faces, and no face conditions intelligently."""
    global prev_face_coords, no_face_counter, last_error

    current_time = time.time()
    results = face_detection.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    new_error = None  # Store the error for this run

    if results.detections:
        no_face_counter = 0  # Reset no-face counter
        face_count = len(results.detections)

        # Detect multiple faces
        if face_count > NO_OF_FACES_THRESHOLD:
            new_error = "Multiple faces detected!"
            if "No face detected!" in alerts:
                    del alerts["No face detected!"]

        # Detect face shift
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
            shift_distance = (
                (prev_face_coords[0] - current_coords[0]) ** 2
                + (prev_face_coords[1] - current_coords[1]) ** 2
            ) ** 0.5

            # if shift_distance > HEAD_SHIFT_THRESHOLD:
            #     if current_time - LAST_ALERT_TIME["face_shift"] > COOLDOWN_SECONDS:
            #         add_alert("Face shift detected!")
            #         LAST_ALERT_TIME["face_shift"] = current_time

        prev_face_coords = current_coords  # Update face coordinates
    else:
        no_face_counter += 1

        if no_face_counter >= NO_FACE_THRESHOLD:
            new_error = "No face detected!"

    # ✅ Only trigger an alert if the new error is different from the last error
    if new_error and new_error != last_error:
        add_alert(new_error)
        last_error = new_error  # Update last error
    elif not new_error:
        last_error = None  # Reset when no issue is detected


def monitor_sound_levels():
    """Monitors sound levels for loud noises."""
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
    """Detects if the environment is a virtual machine."""
    vm_indicators = ["VirtualBox", "VMware", "Hyper-V", "QEMU", "Parallels"]
    try:
        if platform.system() == "Windows":
            bios_info = subprocess.check_output(
                "wmic bios get smbiosbiosversion", shell=True
            ).decode()
        else:
            bios_info = subprocess.check_output(
                "dmidecode -s bios-version", shell=True
            ).decode()

        for indicator in vm_indicators:
            if indicator.lower() in bios_info.lower():
                add_alert(f"Virtual Machine detected ({indicator})!")
                break
    except Exception as e:
        add_alert(f"Error detecting VM environment: {e}")


# Add a lock for thread safety when accessing the `alerts` dictionary
alert_lock = threading.Lock()


@app.route("/get_alerts")
def get_alerts():
    """Returns alerts as JSON."""
    with alert_lock:  # Ensures thread-safe access to `alerts`
        alert_data = [
            {"message": alert, "count": count} for alert, count in alerts.items()
        ]
    return jsonify({"alerts": alert_data})


def generate_video_feed():
    """Generates frames for the video feed with face detection."""
    cap = cv2.VideoCapture(1)
    with mp_face_detection.FaceDetection(
        min_detection_confidence=0.7
    ) as face_detection:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            detect_face_shifts_and_multiple_faces(frame, face_detection)

            _, buffer = cv2.imencode(".jpg", frame)
            frame = buffer.tobytes()

            yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")

    cap.release()


@app.route("/video_feed")
def video_feed():
    """Serves the video feed to the frontend."""
    return Response(
        generate_video_feed(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/")
def index():
    """Renders the main page."""
    return render_template("index.html")


if __name__ == "__main__":
    threading.Thread(target=monitor_tab_switching, daemon=True).start()
    threading.Thread(target=monitor_sound_levels, daemon=True).start()
    detect_vm_environment()
    app.run(debug=True, host="0.0.0.0")
