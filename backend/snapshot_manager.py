from datetime import datetime
from pathlib import Path

import cv2


class SnapshotManager:
    """Saves evidence images for denied and review events."""

    def __init__(self, base_folder: str = "logs/snapshots"):
        self.base_folder = Path(base_folder)
        self.base_folder.mkdir(parents=True, exist_ok=True)

    def save(self, frame, worker, decision) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%H-%M-%S")

        status_folder = decision.status.lower().replace(" ", "_")

        folder = self.base_folder / today / status_folder
        folder.mkdir(parents=True, exist_ok=True)

        safe_worker_name = worker.name.lower().replace(" ", "_")

        filename = (
            f"{timestamp}_"
            f"{worker.worker_id}_"
            f"{safe_worker_name}.jpg"
        )

        file_path = folder / filename

        success = cv2.imwrite(str(file_path), frame)

        if not success:
            raise RuntimeError(
                f"Could not save snapshot to: {file_path}"
            )

        return str(file_path)