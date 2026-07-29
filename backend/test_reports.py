"""Focused local-CSV analytics and reports-route checks."""

import csv
import tempfile
from pathlib import Path

import dashboard


CSV_FIELDNAMES = [
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


def event(**overrides: str) -> dict[str, str]:
    values = {fieldname: "" for fieldname in CSV_FIELDNAMES}
    values.update(
        {
            "timestamp": "2026-07-29T12:00:00",
            "worker_id": "1002",
            "worker_name": "John Smith",
            "status": "ACCESS DENIED",
            "reason": "Required PPE missing: helmet.",
        }
    )
    values.update(overrides)
    return values


def test_analytics_calculations() -> None:
    events = [
        event(status="ACCESS GRANTED", reason="Helmet and vest detected consistently."),
        event(
            status="ACCESS GRANTED",
            worker_id="1001",
            worker_name="Asha Patel",
            reason="Helmet and vest detected consistently.",
        ),
        event(reason="Required PPE missing: helmet."),
        event(
            status="MANAGER REVIEW",
            reason="Helmet exemption verified, but required hi-vis vest is missing.",
            review_status="OVERRIDDEN",
        ),
        event(
            status="ACCESS DENIED",
            reason="Required PPE missing: helmet, vest.",
            review_status="DENIAL_CONFIRMED",
        ),
    ]

    analytics = dashboard.calculate_report_analytics(events)

    assert analytics["total"] == 5
    assert analytics["granted"] == 2
    assert analytics["denied"] == 2
    assert analytics["review"] == 1
    assert analytics["human_overrides"] == 1
    assert analytics["denial_confirmations"] == 1
    assert analytics["compliance_percentage"] == 40.0
    assert analytics["most_common_missing_ppe"] == "helmet"
    assert analytics["most_common_missing_ppe_count"] == 2
    assert analytics["worker_concerns"][0]["total"] == 3


def test_empty_and_missing_logs() -> None:
    with tempfile.TemporaryDirectory() as temporary_directory:
        missing_path = Path(temporary_directory) / "missing.csv"
        assert dashboard.load_events(missing_path) == []

    analytics = dashboard.calculate_report_analytics([])
    assert analytics["total"] == 0
    assert analytics["compliance_percentage"] is None
    assert analytics["most_common_missing_ppe"] is None
    assert analytics["worker_concerns"] == []


def test_csv_loading_and_reports_route() -> None:
    with tempfile.TemporaryDirectory() as temporary_directory:
        log_path = Path(temporary_directory) / "events.csv"
        rows = [
            event(timestamp="2026-07-29T10:00:00"),
            event(
                timestamp="2026-07-29T11:00:00",
                status="ACCESS GRANTED",
                reason="Helmet and vest detected consistently.",
            ),
        ]
        with log_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)

        loaded_events = dashboard.load_events(log_path)
        assert len(loaded_events) == 2
        assert loaded_events[0]["status"] == "ACCESS GRANTED"

    dashboard.app.config["TESTING"] = True
    response = dashboard.app.test_client().get("/reports")
    assert response.status_code == 200
    assert b"Prototype analytics based only on local CSV audit records." in response.data
    assert b"PPE compliance percentage" in response.data
    assert b"Repeat safety concerns by worker" in response.data


def main() -> None:
    test_analytics_calculations()
    test_empty_and_missing_logs()
    test_csv_loading_and_reports_route()
    print("Reports analytics checks passed!")


if __name__ == "__main__":
    main()
