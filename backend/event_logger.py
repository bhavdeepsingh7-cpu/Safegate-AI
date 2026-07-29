import csv
from datetime import datetime
from pathlib import Path


class EventLogger:
    """Stores SafeGate access decisions in a CSV file."""

    FIELDNAMES = [
        "timestamp",
        "worker_id",
        "worker_name",
        "role",
        "helmet_exempt",
        "status",
        "helmet_frames",
        "vest_frames",
        "frames_checked",
        "reason",
        "snapshot_path",
        "override_status",
        "override_manager",
        "override_time",
    ]

    def __init__(
        self,
        log_path: str = "logs/access_events.csv",
    ):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not self.log_path.exists():
            self._create_log_file()

    def _create_log_file(self) -> None:
        with self.log_path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=self.FIELDNAMES,
            )

            writer.writeheader()

    def log(
        self,
        worker,
        decision,
        snapshot_path: str = "",
    ) -> None:
        with self.log_path.open(
            "a",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=self.FIELDNAMES,
            )

            writer.writerow(
                {
                    "timestamp": datetime.now().isoformat(
                        timespec="seconds"
                    ),
                    "worker_id": worker.worker_id,
                    "worker_name": worker.name,
                    "role": worker.role,
                    "helmet_exempt": worker.helmet_exempt,
                    "status": decision.status,
                    "helmet_frames": decision.helmet_frames,
                    "vest_frames": decision.vest_frames,
                    "frames_checked": decision.frames_checked,
                    "reason": decision.reason,
                    "snapshot_path": snapshot_path,
                    "override_status": "",
                    "override_manager": "",
                    "override_time": "",
                }
            )