import cv2
from ultralytics import YOLO

# Change this path if the find command showed a different folder.
MODEL_PATH = "runs/detect/runs/safegate_ppe/weights/best.pt"

print("Loading SafeGate PPE model...")

model = YOLO(MODEL_PATH)

print("Model loaded successfully.")
print("Detected classes:", model.names)

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Error: Camera could not be opened.")
    raise SystemExit

print("SafeGate AI is running.")
print("Press Q to close.")

while True:
    success, frame = camera.read()

    if not success:
        print("Error: Camera frame could not be read.")
        break

    results = model.predict(
        source=frame,
        conf=0.40,
        verbose=False
    )

    display_frame = results[0].plot()

    cv2.putText(
        display_frame,
        "SafeGate AI - PPE Detection",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 255, 255),
        2
    )

    cv2.imshow("SafeGate AI", display_frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()