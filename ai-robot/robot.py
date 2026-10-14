import os
import threading
import cv2
import mediapipe as mp
import pyttsx3
import sounddevice as sd
import speech_recognition as sr
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

folder = os.path.dirname(os.path.abspath(__file__))

# ---------- shared state (camera thread writes, voice thread reads) ----------
state = {"faces": 0, "fingers": 0, "running": True}

# ---------- VOICE THREAD: ears + brain + mouth ----------
def voice_loop():
    engine = pyttsx3.init()          # created inside this thread on purpose
    recognizer = sr.Recognizer()
    FS = 16000

    def speak(text):
        print("Robot:", text)
        engine.say(text)
        engine.runAndWait()

    def listen(seconds=4):
        print("Listening... speak now")
        rec = sd.rec(int(seconds * FS), samplerate=FS, channels=1, dtype="int16")
        sd.wait()
        audio = sr.AudioData(rec.tobytes(), FS, 2)
        try:
            text = recognizer.recognize_google(audio)
            print("You:", text)
            return text.lower()
        except sr.UnknownValueError:
            return ""
        except sr.RequestError:
            speak("Internet problem")
            return ""

    speak("Hello, I am ready. Try: count my fingers, detect my face, or repeat hello.")

    while state["running"]:
        cmd = listen()
        if not cmd:
            continue

        if "stop" in cmd or "exit" in cmd or "quit" in cmd:
            speak("Goodbye")
            state["running"] = False
        elif "finger" in cmd:
            n = state["fingers"]
            speak(f"I can see {n} finger" + ("" if n == 1 else "s"))
        elif "face" in cmd:
            n = state["faces"]
            if n == 0:
                speak("I cannot see any face")
            else:
                speak(f"I can see {n} face" + ("" if n == 1 else "s"))
        elif cmd.startswith("repeat") or cmd.startswith("say"):
            words = cmd.split(" ", 1)
            speak(words[1] if len(words) > 1 else "Repeat what?")
        elif "hello" in cmd or "hi" in cmd.split():
            speak("Hello! I am your robot.")
        else:
            speak("Sorry, I do not know that command")


# ---------- CAMERA (main thread): eyes ----------
face_det = vision.FaceDetector.create_from_options(
    vision.FaceDetectorOptions(
        base_options=mp_python.BaseOptions(model_asset_path=os.path.join(folder, "face.tflite")),
        min_detection_confidence=0.6))

hand_det = vision.HandLandmarker.create_from_options(
    vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=os.path.join(folder, "hand.task")),
        num_hands=2))


def count_fingers(lm, label):
    fingers = 0
    if label == "Right":
        fingers += lm[4].x < lm[3].x
    else:
        fingers += lm[4].x > lm[3].x
    for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
        fingers += lm[tip].y < lm[pip].y
    return int(fingers)


threading.Thread(target=voice_loop, daemon=True).start()

cap = cv2.VideoCapture(0)

while state["running"]:
    ret, frame = cap.read()
    if not ret:
        print("Camera not found")
        break
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    faces = face_det.detect(image).detections
    for d in faces:
        b = d.bounding_box
        cv2.rectangle(frame, (b.origin_x, b.origin_y),
                      (b.origin_x + b.width, b.origin_y + b.height), (0, 255, 0), 2)

    total = 0
    hands = hand_det.detect(image)
    for lms, handed in zip(hands.hand_landmarks, hands.handedness):
        total += count_fingers(lms, handed[0].category_name)
        for p in lms:
            cv2.circle(frame, (int(p.x * w), int(p.y * h)), 4, (255, 0, 0), -1)

    state["faces"] = len(faces)
    state["fingers"] = total

    cv2.putText(frame, f"Faces: {len(faces)}  Fingers: {total}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.imshow("Robot - say 'stop' or press Q to quit", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        state["running"] = False

cap.release()
cv2.destroyAllWindows()
