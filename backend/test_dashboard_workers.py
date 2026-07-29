"""Focused Flask route checks for browser-based worker management."""

import tempfile
from pathlib import Path

import dashboard
from worker_db import WorkerDatabase


def main() -> None:
    original_database = dashboard.worker_database
    dashboard.app.config["TESTING"] = True

    with tempfile.TemporaryDirectory() as temporary_directory:
        database_path = Path(temporary_directory) / "workers.db"
        dashboard.worker_database = WorkerDatabase(
            database_path=str(database_path)
        )
        client = dashboard.app.test_client()

        response = client.get("/workers")
        assert response.status_code == 200
        assert b"Worker Management" in response.data

        response = client.post(
            "/workers",
            data={"worker_id": "", "name": "", "role": ""},
            follow_redirects=True,
        )
        assert b"Worker ID, name, and role are required." in response.data

        worker_data = {
            "worker_id": "9001",
            "name": "Dashboard Test Worker",
            "role": "Safety Marshal",
            "notes": "Created by dashboard route test.",
            "helmet_exempt": "on",
            "active": "on",
        }
        response = client.post(
            "/workers",
            data=worker_data,
            follow_redirects=True,
        )
        assert b"Added worker Dashboard Test Worker." in response.data
        assert dashboard.worker_database.get_worker("9001") is not None

        response = client.post(
            "/workers",
            data=worker_data,
            follow_redirects=True,
        )
        assert b"Worker ID 9001 already exists." in response.data

        response = client.get("/workers?search=Marshal")
        assert b"Dashboard Test Worker" in response.data

        response = client.get("/workers?search=9001")
        assert b"Dashboard Test Worker" in response.data

        response = client.get("/workers?search=Dashboard%20Test")
        assert b"Dashboard Test Worker" in response.data

        response = client.post(
            "/workers/9001/edit",
            data={
                "name": "Updated Dashboard Worker",
                "role": "Senior Safety Marshal",
                "notes": "Updated by dashboard route test.",
                "active": "on",
            },
            follow_redirects=True,
        )
        assert b"Updated worker Updated Dashboard Worker." in response.data

        worker = dashboard.worker_database.get_worker("9001")
        assert worker is not None
        assert worker.helmet_exempt is False
        assert worker.role == "Senior Safety Marshal"

        response = client.post(
            "/workers/9001/status",
            data={"active": "false"},
            follow_redirects=True,
        )
        assert b"Worker 9001 deactivated." in response.data
        assert dashboard.worker_database.get_worker("9001").active is False

        response = client.post(
            "/workers/9001/status",
            data={"active": "true"},
            follow_redirects=True,
        )
        assert b"Worker 9001 activated." in response.data
        assert dashboard.worker_database.get_worker("9001").active is True

        dashboard.live_feed_service.select_worker(worker)
        response = client.post(
            "/workers/9001/delete",
            follow_redirects=True,
        )
        assert b"Clear the active verification session" in response.data
        assert dashboard.worker_database.get_worker("9001") is not None

        dashboard.live_feed_service.clear_worker()
        response = client.post(
            "/workers/9001/delete",
            follow_redirects=True,
        )
        assert b"Deleted worker 9001." in response.data
        assert dashboard.worker_database.get_worker("9001") is None

    dashboard.worker_database = original_database
    print("Dashboard worker-management route checks passed!")


if __name__ == "__main__":
    main()
