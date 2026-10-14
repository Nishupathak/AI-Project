import os
import urllib.request
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

BASE = "https://storage.googleapis.com/mediapipe-models/"
MODELS = {
    "face.tflite": BASE + "face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite",
    "hand.task": BASE + "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
}

folder = os.path.dirname(os.path.abspath(__file__))
for name, url in MODELS.items():
    path = os.path.join(folder, name)
    if not os.path.exists(path):
        print("Downloading", name, "...")
        urllib.request.urlretrieve(url, path)

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


cap = cv2.VideoCapture(0)

while True:
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

    cv2.putText(frame, f"Faces: {len(faces)}  Fingers: {total}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.imshow("Robot Eyes - press Q to quit", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
