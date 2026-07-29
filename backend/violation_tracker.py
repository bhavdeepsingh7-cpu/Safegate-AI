import csv
from pathlib import Path


class ViolationTracker:
    """Counts recent denied and review events for each worker."""

    def __init__(
        self,
        log_path: str = "logs/access_events.csv",
        warning_threshold: int = 3,
    ):
        self.log_path = Path(log_path)
        self.warning_threshold = warning_threshold

    def count_violations(self, worker_id: str) -> int:
        if not self.log_path.exists():
            return 0

        with self.log_path.open(
            "r",
            newline="",
            encoding="utf-8",
        ) as file:
            events = list(csv.DictReader(file))

        return sum(
            event.get("worker_id") == worker_id
            and event.get("status")
            in {"ACCESS DENIED", "MANAGER REVIEW"}
            for event in events
        )

    def get_warning(self, worker_id: str) -> str:
        count = self.count_violations(worker_id)

        if count >= self.warning_threshold:
            return (
                f"REPEAT SAFETY ALERT: "
                f"{count} denied/review events recorded."
            )

        return ""