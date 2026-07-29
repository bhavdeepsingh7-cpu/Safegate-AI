"""Focused checks for manager review resolutions in the CSV audit log."""

import csv
import tempfile
from pathlib import Path

import dashboard
from event_logger import EventLogger


LEGACY_FIELDNAMES = [
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
    "override_reason",
    "override_time",
]


def write_legacy_events(log_path: Path) -> None:
    """Create legacy events so the audit schema migration is also covered."""

    events = [
        {
            "timestamp": "2026-07-29T10:00:00",
            "worker_id": "7001",
            "worker_name": "Review Worker",
            "role": "Electrician",
            "helmet_exempt": "False",
            "status": "MANAGER REVIEW",
            "helmet_frames": "7",
            "vest_frames": "9",
            "frames_checked": "15",
            "reason": "PPE detections are unclear or inconsistent.",
            "snapshot_path": "logs/snapshots/review.jpg",
            "override_status": "",
            "override_manager": "",
            "override_reason": "",
            "override_time": "",
        },
        {
            "timestamp": "2026-07-29T10:05:00",
            "worker_id": "7002",
            "worker_name": "Denied Worker",
            "role": "Visitor",
            "helmet_exempt": "False",
            "status": "ACCESS DENIED",
            "helmet_frames": "0",
            "vest_frames": "15",
            "frames_checked": "15",
            "reason": "Required PPE missing: helmet.",
            "snapshot_path": "logs/snapshots/denied.jpg",
            "override_status": "",
            "override_manager": "",
            "override_reason": "",
            "override_time": "",
        },
    ]

    with log_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=LEGACY_FIELDNAMES)
        writer.writeheader()
        writer.writerows(events)


def read_events(log_path: Path) -> list[dict]:
    with log_path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        assert reader.fieldnames == EventLogger.FIELDNAMES
        return list(reader)


def main() -> None:
    original_log_path = dashboard.LOG_PATH
    original_event_logger = dashboard.event_logger
    dashboard.app.config["TESTING"] = True

    try:
        with tempfile.TemporaryDirectory() as temporary_directory:
            log_path = Path(temporary_directory) / "access_events.csv"
            write_legacy_events(log_path)

            dashboard.LOG_PATH = log_path
            dashboard.event_logger = EventLogger(log_path=str(log_path))
            client = dashboard.app.test_client()

            # Both unresolved reviewable outcomes appear in the pending queue.
            response = client.get("/logs")
            assert b"Review Worker" in response.data
            assert b"Denied Worker" in response.data
            assert response.data.count(b"Approve override") == 2
            assert response.data.count(b"Confirm denial") == 2

            # Name and reason are mandatory for either manager action.
            response = client.post(
                "/logs/0/override",
                data={"manager_name": "", "manager_reason": ""},
                follow_redirects=True,
            )
            assert b"Manager name and reason are required." in response.data
            response = client.post(
                "/logs/1/confirm-denial",
                data={"manager_name": "Site Manager", "manager_reason": ""},
                follow_redirects=True,
            )
            assert b"Manager name and reason are required." in response.data

            # Override approval resolves the event but preserves automation data.
            response = client.post(
                "/logs/0/override",
                data={
                    "manager_name": "Site Manager",
                    "manager_reason": "PPE was checked manually at the gate.",
                },
                follow_redirects=True,
            )
            assert b"Human override recorded." in response.data
            rows = read_events(log_path)
            assert rows[0]["status"] == "MANAGER REVIEW"
            assert rows[0]["reason"] == "PPE detections are unclear or inconsistent."
            assert rows[0]["snapshot_path"] == "logs/snapshots/review.jpg"
            assert rows[0]["review_status"] == "OVERRIDDEN"
            assert rows[0]["manager_name"] == "Site Manager"
            assert rows[0]["manager_action_time"]

            response = client.get("/logs")
            assert b"Review Worker" in response.data  # Full audit history.
            assert response.data.count(b"Approve override") == 1
            assert response.data.count(b"Confirm denial") == 1

            # Denial confirmation resolves the remaining event without rewriting it.
            response = client.post(
                "/logs/1/confirm-denial",
                data={
                    "manager_name": "Site Manager",
                    "manager_reason": "Worker did not have the required helmet.",
                },
                follow_redirects=True,
            )
            assert b"Denial confirmation recorded." in response.data
            rows = read_events(log_path)
            assert rows[1]["status"] == "ACCESS DENIED"
            assert rows[1]["reason"] == "Required PPE missing: helmet."
            assert rows[1]["snapshot_path"] == "logs/snapshots/denied.jpg"
            assert rows[1]["review_status"] == "DENIAL_CONFIRMED"
            assert rows[1]["manager_name"] == "Site Manager"
            assert rows[1]["manager_action_time"]

            response = client.get("/logs")
            assert b"No denied or manager-review events are awaiting review." in response.data
            assert b"Review Worker" in response.data
            assert b"Denied Worker" in response.data
    finally:
        dashboard.LOG_PATH = original_log_path
        dashboard.event_logger = original_event_logger

    print("Manager review resolution checks passed!")


if __name__ == "__main__":
    main()
