import cv2

from camera import Camera
from decision_engine import DecisionEngine
from detector import PPEDetector
from event_logger import EventLogger
from snapshot_manager import SnapshotManager
from violation_tracker import ViolationTracker
from worker_db import WorkerDatabase


MODEL_PATH = "runs/detect/runs/safegate_ppe/weights/best.pt"


def select_worker(database: WorkerDatabase):
    print("\nRegistered demo workers:")
    print("1001 - Bhavdeep Singh - Helmet exemption")
    print("1002 - John Smith - Standard PPE")
    print("1003 - Amelia Jones - Inactive")
    print()

    worker_id = input("Enter worker ID: ").strip()
    worker = database.get_worker(worker_id)

    if worker is None:
        print("ACCESS DENIED: Worker ID was not found.")
        return None

    if not worker.active:
        print(f"ACCESS DENIED: {worker.name}'s access is inactive.")
        return None

    print("\nWorker verified:")
    print(f"ID: {worker.worker_id}")
    print(f"Name: {worker.name}")
    print(f"Role: {worker.role}")
    print(f"Helmet exemption: {worker.helmet_exempt}")
    print()

    return worker


def draw_status(frame, decision, worker, violation_warning):
    cv2.rectangle(
        frame,
        (0, 0),
        (frame.shape[1], 215),
        (0, 0, 0),
        -1,
    )

    cv2.putText(
        frame,
        f"Worker: {worker.name} ({worker.worker_id})",
        (20, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2,
    )

    exemption_text = "YES" if worker.helmet_exempt else "NO"

    cv2.putText(
        frame,
        f"Helmet exemption: {exemption_text}",
        (20, 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2,
    )

    cv2.putText(
        frame,
        f"Status: {decision.status}",
        (20, 95),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.85,
        (255, 255, 255),
        2,
    )

    cv2.putText(
        frame,
        f"Helmet: {decision.helmet_frames}/{decision.frames_checked}",
        (20, 130),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (255, 255, 255),
        2,
    )

    cv2.putText(
        frame,
        f"Vest: {decision.vest_frames}/{decision.frames_checked}",
        (300, 130),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (255, 255, 255),
        2,
    )

    cv2.putText(
        frame,
        decision.reason,
        (20, 165),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (255, 255, 255),
        1,
    )

    if violation_warning:
        cv2.putText(
            frame,
            violation_warning,
            (20, 200),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 0, 255),
            2,
        )


def main():
    worker_database = WorkerDatabase()
    worker = select_worker(worker_database)

    if worker is None:
        return

    detector = PPEDetector(
        model_path=MODEL_PATH,
        confidence=0.25,
    )

    camera = Camera(camera_index=0)

    decision_engine = DecisionEngine(
        history_size=15,
        grant_threshold=10,
        deny_threshold=10,
        helmet_required=not worker.helmet_exempt,
    )

    event_logger = EventLogger()
    snapshot_manager = SnapshotManager()
    violation_tracker = ViolationTracker(
        warning_threshold=3,
    )

    last_logged_status = None
    violation_warning = violation_tracker.get_warning(
        worker.worker_id
    )

    print("SafeGate AI is running.")
    print("Press Q to close.")

    if violation_warning:
        print(violation_warning)

    try:
        while True:
            frame = camera.read()
            result = detector.detect(frame)

            detected_classes = detector.get_detected_classes(
                result
            )

            decision = decision_engine.update(
                detected_classes
            )

            display_frame = result.plot()

            draw_status(
                display_frame,
                decision,
                worker,
                violation_warning,
            )

            if (
                decision.status != "SCANNING"
                and decision.status != last_logged_status
            ):
                snapshot_path = ""

                if decision.status in {
                    "ACCESS DENIED",
                    "MANAGER REVIEW",
                }:
                    snapshot_path = snapshot_manager.save(
                        display_frame,
                        worker,
                        decision,
                    )

                    print(f"Snapshot saved: {snapshot_path}")

                event_logger.log(
                    worker=worker,
                    decision=decision,
                    snapshot_path=snapshot_path,
                )

                last_logged_status = decision.status

                violation_warning = violation_tracker.get_warning(
                    worker.worker_id
                )

                print(
                    f"Logged decision for {worker.name}: "
                    f"{decision.status} | {decision.reason}"
                )

                if violation_warning:
                    print(violation_warning)

            cv2.imshow("SafeGate AI", display_frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    except RuntimeError as error:
        print(error)

    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()