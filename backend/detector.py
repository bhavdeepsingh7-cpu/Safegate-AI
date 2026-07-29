from pathlib import Path

from ultralytics import YOLO


class PPEDetector:
    """Loads the SafeGate PPE model and detects PPE in video frames."""

    def __init__(self, model_path: str, confidence: float = 0.25):
        self.model_path = Path(model_path)
        self.confidence = confidence

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"PPE model could not be found at: {self.model_path}"
            )

        print(f"Loading PPE model from: {self.model_path}")

        self.model = YOLO(str(self.model_path))

        print("PPE model loaded successfully.")
        print("Available classes:", self.model.names)

    def detect(self, frame):
        """Run detection and return the YOLO result."""

        results = self.model.predict(
            source=frame,
            conf=self.confidence,
            iou=0.45,
            imgsz=640,
            verbose=False,
        )

        return results[0]

    def get_detected_classes(self, result) -> list[str]:
        """Convert YOLO detections into ordinary class-name strings."""

        detected_classes = []

        if result.boxes is None:
            return detected_classes

        for class_id in result.boxes.cls.tolist():
            class_name = self.model.names[int(class_id)]
            detected_classes.append(class_name)

        return detected_classes