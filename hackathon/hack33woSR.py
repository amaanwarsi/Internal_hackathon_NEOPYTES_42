import cv2
import mediapipe as mp  # type: ignore
import pygetwindow as gw # type: ignore
import time
import threading
import pyaudio
import numpy as np
from pynput import keyboard  # type: ignore
import pyperclip  # type: ignore
import subprocess
import platform


mp_face_detection = mp.solutions.face_detection
mp_drawing = mp.solutions.drawing_utils

TAB_CHECK_INTERVAL = 2  
HEAD_SHIFT_THRESHOLD = 20  
NO_FACE_THRESHOLD = 30  
NO_OF_FACES_THRESHOLD = 1 
VOICE_THRESHOLD = 5000

prev_face_coords = None
no_face_counter = 0
is_voice_alert_triggered = False

def monitor_tab_switching():
    previous_window = gw.getActiveWindow().title if gw.getActiveWindow() else None
    while True:
        current_window = gw.getActiveWindow()
        if current_window and current_window.title != previous_window:
            print("ALERT: Tab switching detected!")
            previous_window = current_window.title
        time.sleep(TAB_CHECK_INTERVAL)

def detect_face_shifts_and_multiple_faces(frame, face_detection):
    global prev_face_coords, no_face_counter

    results = face_detection.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    face_detected = False
    face_count = 0

    if results.detections:
        face_detected = True
        no_face_counter = 0
        face_count = len(results.detections)

        if face_count > NO_OF_FACES_THRESHOLD:
            cv2.putText(
                frame,
                "ALERT: Multiple faces detected!",
                (50, 150),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2,
            )
            print(f"ALERT: {face_count} faces detected!")

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
                cv2.putText(
                    frame,
                    "ALERT: Face shift detected!",
                    (50, 100),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 255),
                    2,
                )
                print("ALERT: Face shift detected!")

        prev_face_coords = current_coords

        mp_drawing.draw_detection(frame, detection)
    else:
        no_face_counter += 1
        if no_face_counter >= NO_FACE_THRESHOLD:
            cv2.putText(
                frame,
                "ALERT: No face detected!",
                (50, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2,
            )
            print("ALERT: No face detected!")

    return face_detected


    
def block_clipboard_operations():
    """Continuously clears clipboard to block copy, cut, and paste operations."""
    while True:
        pyperclip.copy("")  
        time.sleep(1) 

def on_key_press(key):
    """Intercepts key presses to block common copy/paste shortcuts."""
    try:
        if key in [keyboard.Key.print_screen, keyboard.Key.ctrl_l]:
            print("ALERT: Screenshot or clipboard operation detected!")
            return False 
    except Exception as e:
        print(f"Error in key press monitoring: {e}")

def monitor_keyboard():
    """Monitors for specific key events."""
    with keyboard.Listener(on_press=on_key_press) as listener:
        listener.join()

threading.Thread(target=block_clipboard_operations, daemon=True).start()
threading.Thread(target=monitor_keyboard, daemon=True).start()


def monitor_sound_levels():
    global is_voice_alert_triggered

    p = pyaudio.PyAudio()

    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=44100,
        input=True,
        frames_per_buffer=1024,
    )

    print("Monitoring sound levels...")

    cooldown_end_time = 0.3

    while True:
        data = stream.read(1024, exception_on_overflow=False)
        audio_data = np.frombuffer(data, dtype=np.int16)

        volume = np.linalg.norm(audio_data)

        current_time = time.time()
        if volume > VOICE_THRESHOLD and current_time >= cooldown_end_time:
            print("ALERT: Loud noise detected!")
            is_voice_alert_triggered = True
            cooldown_end_time = current_time + 1

def detect_vm_environment():
    """Detects if the system is running in a virtual machine."""
    vm_indicators = ["VirtualBox", "VMware", "Hyper-V", "QEMU", "Parallels"]
    detected_vm = False

 
    try:
        if platform.system() == "Windows":
            bios_info = subprocess.check_output("wmic bios get smbiosbiosversion", shell=True).decode()
        else:
            bios_info = subprocess.check_output("dmidecode -s bios-version", shell=True).decode()

        for indicator in vm_indicators:
            if indicator.lower() in bios_info.lower():
                print(f"ALERT: Virtual Machine detected ({indicator})!")
                detected_vm = True
                break
    except Exception as e:
        print(f"Error detecting VM environment: {e}")

    return detected_vm

if detect_vm_environment():
    print("Exam cannot be conducted in a Virtual Machine environment.")


def monitor_exam():

    threading.Thread(target=monitor_tab_switching, daemon=True).start()

    threading.Thread(target=monitor_sound_levels, daemon=True).start()

    cap = cv2.VideoCapture(0)
    with mp_face_detection.FaceDetection(min_detection_confidence=0.7) as face_detection:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            detect_face_shifts_and_multiple_faces(frame, face_detection)

            cv2.imshow("AI Proctoring System", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()

monitor_exam()