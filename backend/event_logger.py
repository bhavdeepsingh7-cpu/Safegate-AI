import csv
from datetime import datetime
from pathlib import Path


class EventLogger:
    """Stores SafeGate access decisions and manager-review audit data in CSV."""

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
        "review_status",
        "manager_name",
        "manager_reason",
        "manager_action_time",
    ]
    REVIEWABLE_STATUSES = {"ACCESS DENIED", "MANAGER REVIEW"}
    RESOLVED_REVIEW_STATUSES = {"OVERRIDDEN", "DENIAL_CONFIRMED"}

    def __init__(self, log_path: str = "logs/access_events.csv"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.log_path.exists():
            self._create_log_file()
        else:
            self._ensure_log_schema()

    def _ensure_log_schema(self) -> None:
        """Migrate prior audit headers without discarding recorded events."""

        with self.log_path.open("r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            existing_fieldnames = reader.fieldnames or []
            rows = list(reader)

        if existing_fieldnames == self.FIELDNAMES:
            return

        temporary_path = self.log_path.with_suffix(f"{self.log_path.suffix}.tmp")
        with temporary_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=self.FIELDNAMES)
            writer.writeheader()

            for row in rows:
                migrated_row = {
                    fieldname: row.get(fieldname, "")
                    for fieldname in self.FIELDNAMES
                }
                if not migrated_row["review_status"]:
                    if row.get("override_status") == "OVERRIDDEN":
                        migrated_row["review_status"] = "OVERRIDDEN"
                    elif row.get("status") in self.REVIEWABLE_STATUSES:
                        migrated_row["review_status"] = "PENDING"

                migrated_row["manager_name"] = (
                    migrated_row["manager_name"]
                    or row.get("override_manager", "")
                )
                migrated_row["manager_reason"] = (
                    migrated_row["manager_reason"]
                    or row.get("override_reason", "")
                )
                migrated_row["manager_action_time"] = (
                    migrated_row["manager_action_time"]
                    or row.get("override_time", "")
                )
                writer.writerow(migrated_row)

        temporary_path.replace(self.log_path)

    def _create_log_file(self) -> None:
        with self.log_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=self.FIELDNAMES)
            writer.writeheader()

    def log(self, worker, decision, snapshot_path: str = "") -> None:
        """Append an automated decision, keeping its review state separate."""

        self._ensure_log_schema()
        with self.log_path.open("a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=self.FIELDNAMES)
            writer.writerow(
                {
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
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
                    "review_status": (
                        "PENDING"
                        if decision.status in self.REVIEWABLE_STATUSES
                        else ""
                    ),
                    "manager_name": "",
                    "manager_reason": "",
                    "manager_action_time": "",
                }
            )

    def record_manager_action(
        self,
        event_index: int,
        manager_name: str,
        manager_reason: str,
        review_status: str,
    ) -> bool:
        """Resolve an eligible event without changing its automated decision."""

        manager_name = manager_name.strip()
        manager_reason = manager_reason.strip()
        if (
            not manager_name
            or not manager_reason
            or review_status not in self.RESOLVED_REVIEW_STATUSES
        ):
            return False

        self._ensure_log_schema()
        with self.log_path.open("r", newline="", encoding="utf-8") as file:
            rows = list(csv.DictReader(file))

        if event_index < 0 or event_index >= len(rows):
            return False

        event = rows[event_index]
        if (
            event.get("status") not in self.REVIEWABLE_STATUSES
            or event.get("review_status") != "PENDING"
        ):
            return False

        event["review_status"] = review_status
        event["manager_name"] = manager_name
        event["manager_reason"] = manager_reason
        event["manager_action_time"] = datetime.now().isoformat(timespec="seconds")

        with self.log_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=self.FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)

        return True
