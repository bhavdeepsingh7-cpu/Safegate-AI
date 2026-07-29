import threading
import time
from pathlib import Path

import cv2

from camera import Camera
from detector import PPEDetector


class LiveFeedService:
    """Runs PPE detection and supplies JPEG frames to Flask."""

    def __init__(
        self,
        model_path: str,
        confidence: float = 0.25,
        camera_index: int = 0,
    ):
        self.model_path = Path(model_path)
        self.confidence = confidence
        self.camera_index = camera_index

        self.detector = None
        self.camera = None

        self.latest_frame = None
        self.frame_lock = threading.Lock()

        self.running = False
        self.thread = None

        self.error_message = ""

    def start(self) -> None:
        """Start camera processing in a background thread."""

        if self.running:
            return

        self.running = True
        self.error_message = ""

        self.thread = threading.Thread(
            target=self._process_camera,
            daemon=True,
        )

        self.thread.start()

    def _process_camera(self) -> None:
        """Capture frames and run YOLO continuously."""

        try:
            self.detector = PPEDetector(
                model_path=str(self.model_path),
                confidence=self.confidence,
            )

            self.camera = Camera(
                camera_index=self.camera_index
            )

            previous_time = time.time()

            while self.running:
                frame = self.camera.read()

                result = self.detector.detect(frame)

                display_frame = result.plot()

                current_time = time.time()
                elapsed_time = current_time - previous_time

                fps = (
                    1 / elapsed_time
                    if elapsed_time > 0
                    else 0
                )

                previous_time = current_time

                detected_classes = (
                    self.detector.get_detected_classes(
                        result
                    )
                )

                class_text = (
                    ", ".join(detected_classes)
                    if detected_classes
                    else "No PPE detected"
                )

                cv2.rectangle(
                    display_frame,
                    (0, 0),
                    (display_frame.shape[1], 82),
                    (5, 11, 19),
                    -1,
                )

                cv2.putText(
                    display_frame,
                    "SafeGate AI - Live PPE Detection",
                    (18, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                )

                cv2.putText(
                    display_frame,
                    f"Detected: {class_text}",
                    (18, 58),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.48,
                    (255, 255, 255),
                    1,
                )

                cv2.putText(
                    display_frame,
                    f"FPS: {fps:.1f}",
                    (
                        display_frame.shape[1] - 100,
                        30,
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (56, 216, 139),
                    1,
                )

                success, encoded_frame = cv2.imencode(
                    ".jpg",
                    display_frame,
                    [
                        cv2.IMWRITE_JPEG_QUALITY,
                        82,
                    ],
                )

                if not success:
                    continue

                with self.frame_lock:
                    self.latest_frame = (
                        encoded_frame.tobytes()
                    )

        except Exception as error:
            self.error_message = str(error)

            print(
                f"Live camera service error: {error}"
            )

        finally:
            if self.camera is not None:
                self.camera.release()

            self.camera = None
            self.running = False

    def generate_frames(self):
        """Yield frames in MJPEG format for the browser."""

        self.start()

        while True:
            with self.frame_lock:
                frame = self.latest_frame

            if frame is None:
                if not self.running:
                    break

                time.sleep(0.1)
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + frame
                + b"\r\n"
            )

            time.sleep(0.03)

    def stop(self) -> None:
        """Stop camera processing safely."""

        self.running = False

        if (
            self.thread is not None
            and self.thread.is_alive()
        ):
            self.thread.join(timeout=2)

        self.thread = None
        self.latest_frame = None
        self.error_message = ""

        if self.camera is not None:
            self.camera.release()
            self.camera = None

        print("SafeGate camera stopped.")