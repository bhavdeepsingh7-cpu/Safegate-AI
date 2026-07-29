import threading
import time
from pathlib import Path
from typing import Callable, Optional

import cv2

from camera import Camera
from decision_engine import AccessDecision, DecisionEngine
from detector import PPEDetector
from worker_db import Worker


FinalDecisionHandler = Callable[
    [Worker, AccessDecision, object],
    None,
]


class LiveFeedService:
    """Runs live PPE detection and manages one dashboard session."""

    def __init__(
        self,
        model_path: str,
        confidence: float = 0.25,
        camera_index: int = 0,
        on_final_decision: Optional[FinalDecisionHandler] = None,
    ):
        self.model_path = Path(model_path)
        self.confidence = confidence
        self.camera_index = camera_index
        self.on_final_decision = on_final_decision

        self.detector: Optional[PPEDetector] = None
        self.camera: Optional[Camera] = None
        self.latest_frame: Optional[bytes] = None
        self.frame_lock = threading.Lock()

        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.error_message = ""

        self.state_lock = threading.Lock()
        self.current_worker: Optional[Worker] = None
        self.decision_engine: Optional[DecisionEngine] = None
        self.latest_decision: Optional[AccessDecision] = None
        self.latest_detected_classes: list[str] = []
        self.latest_fps = 0.0
        self.final_decision_recorded = False

    def start(self) -> None:
        """Start camera processing in one background thread."""

        if self.running:
            return

        self.running = True
        self.error_message = ""
        self.thread = threading.Thread(
            target=self._process_camera,
            daemon=True,
        )
        self.thread.start()

    def select_worker(self, worker: Worker) -> None:
        """Start a new policy-aware verification session."""

        with self.state_lock:
            self.current_worker = worker
            self.decision_engine = DecisionEngine(
                history_size=15,
                grant_threshold=10,
                deny_threshold=10,
                helmet_required=not worker.helmet_exempt,
            )
            self.latest_decision = None
            self.latest_detected_classes = []
            self.final_decision_recorded = False

    def clear_worker(self) -> None:
        """Clear the current session without stopping the camera."""

        with self.state_lock:
            self.current_worker = None
            self.decision_engine = None
            self.latest_decision = None
            self.latest_detected_classes = []
            self.final_decision_recorded = False

    def _process_camera(self) -> None:
        """Capture frames, perform inference and update session state."""

        try:
            self.detector = PPEDetector(
                model_path=str(self.model_path),
                confidence=self.confidence,
            )
            self.camera = Camera(camera_index=self.camera_index)
            previous_time = time.time()

            while self.running:
                frame = self.camera.read()
                result = self.detector.detect(frame)
                display_frame = result.plot()
                detected_classes = self.detector.get_detected_classes(result)

                current_time = time.time()
                elapsed_time = current_time - previous_time
                fps = 1 / elapsed_time if elapsed_time > 0 else 0
                previous_time = current_time

                final_event = None

                with self.state_lock:
                    self.latest_detected_classes = detected_classes
                    self.latest_fps = fps

                    if (
                        self.current_worker is not None
                        and self.decision_engine is not None
                    ):
                        self.latest_decision = self.decision_engine.update(
                            detected_classes
                        )

                        if (
                            self.latest_decision.status != "SCANNING"
                            and not self.final_decision_recorded
                        ):
                            self.final_decision_recorded = True
                            final_event = (
                                self.current_worker,
                                self.latest_decision,
                                display_frame.copy(),
                            )

                    worker = self.current_worker
                    decision = self.latest_decision

                self._draw_overlay(
                    display_frame,
                    detected_classes,
                    worker,
                    decision,
                    fps,
                )

                success, encoded_frame = cv2.imencode(
                    ".jpg",
                    display_frame,
                    [cv2.IMWRITE_JPEG_QUALITY, 82],
                )

                if success:
                    with self.frame_lock:
                        self.latest_frame = encoded_frame.tobytes()

                if final_event and self.on_final_decision:
                    try:
                        self.on_final_decision(*final_event)
                    except Exception as error:
                        self.error_message = (
                            "Could not record final decision: "
                            f"{error}"
                        )
                        print(self.error_message)

        except Exception as error:
            self.error_message = str(error)
            print(f"Live camera service error: {error}")

        finally:
            if self.camera is not None:
                self.camera.release()

            self.camera = None
            self.running = False

    @staticmethod
    def _draw_overlay(
        frame,
        detected_classes: list[str],
        worker: Optional[Worker],
        decision: Optional[AccessDecision],
        fps: float,
    ) -> None:
        """Draw dashboard session information on the annotated frame."""

        class_text = ", ".join(detected_classes) or "No PPE detected"

        cv2.rectangle(
            frame,
            (0, 0),
            (frame.shape[1], 110),
            (5, 11, 19),
            -1,
        )
        cv2.putText(
            frame,
            "SafeGate AI - Live PPE Detection",
            (18, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.68,
            (255, 255, 255),
            2,
        )
        cv2.putText(
            frame,
            f"Detected: {class_text}",
            (18, 56),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.47,
            (255, 255, 255),
            1,
        )

        if worker is None:
            session_text = "Waiting for worker selection"
            session_colour = (94, 196, 244)
        elif decision is None:
            session_text = f"Worker: {worker.name} | Initialising"
            session_colour = (94, 196, 244)
        else:
            session_text = f"Worker: {worker.name} | {decision.status}"
            colours = {
                "ACCESS GRANTED": (56, 216, 139),
                "ACCESS DENIED": (99, 99, 255),
                "MANAGER REVIEW": (94, 196, 244),
                "SCANNING": (94, 196, 244),
            }
            session_colour = colours[decision.status]

        cv2.putText(
            frame,
            session_text,
            (18, 84),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.53,
            session_colour,
            2,
        )
        cv2.putText(
            frame,
            f"FPS: {fps:.1f}",
            (frame.shape[1] - 105, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (56, 216, 139),
            1,
        )

    def generate_frames(self):
        """Yield MJPEG frames to the browser."""

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

    def get_live_state(self) -> dict:
        """Return current camera, worker and decision state for the UI."""

        with self.state_lock:
            state = {
                "camera_running": self.running,
                "error": self.error_message,
                "fps": round(self.latest_fps, 1),
                "detected_classes": list(self.latest_detected_classes),
                "worker": None,
                "decision": None,
            }

            if self.current_worker is not None:
                state["worker"] = {
                    "worker_id": self.current_worker.worker_id,
                    "name": self.current_worker.name,
                    "role": self.current_worker.role,
                    "helmet_exempt": self.current_worker.helmet_exempt,
                    "notes": self.current_worker.notes,
                }

            if self.latest_decision is not None:
                state["decision"] = {
                    "status": self.latest_decision.status,
                    "helmet_frames": self.latest_decision.helmet_frames,
                    "vest_frames": self.latest_decision.vest_frames,
                    "frames_checked": self.latest_decision.frames_checked,
                    "reason": self.latest_decision.reason,
                }

            return state

    def stop(self) -> None:
        """Stop camera processing safely without ending Flask."""

        self.running = False

        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=2)

        self.thread = None
        self.latest_frame = None

        if self.camera is not None:
            self.camera.release()
            self.camera = None
