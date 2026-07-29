from ultralytics import YOLO

print("Starting SafeGate PPE model training...")

# Start from the small pretrained YOLO model
model = YOLO("yolo11n.pt")

# Train using the official Construction-PPE dataset
results = model.train(
    data="construction-ppe.yaml",
    epochs=10,
    imgsz=640,
    batch=4,
    device="mps",
    project="runs",
    name="safegate_ppe"
)

print("Training completed successfully!")