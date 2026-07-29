import cv2
from ultralytics import YOLO

model = YOLO("yolo11n.pt")

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Error: Could not open the camera.")
    raise SystemExit

print("Camera started. Press Q to quit.")

while True:
    success, frame = camera.read()

    if not success:
        print("Error: Could not read camera frame.")
        break

    results = model(frame, verbose=False)
    annotated_frame = results[0].plot()

    cv2.imshow("SafeGate AI - Camera Test", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()