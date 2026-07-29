"""Focused Flask route and template checks for gate simulator monitoring."""

import dashboard


def main() -> None:
    dashboard.app.config["TESTING"] = True
    client = dashboard.app.test_client()

    response = client.get("/gate")

    assert response.status_code == 200
    assert b"Simulated gate status" in response.data
    assert (
        b"Simulation mode \xe2\x80\x94 no physical gate hardware is connected."
        in response.data
    )
    for field_id in (
        "gate-monitor-state",
        "gate-monitor-mode",
        "gate-monitor-command",
        "gate-monitor-reason",
        "gate-monitor-timestamp",
        "gate-monitor-camera",
        "gate-monitor-worker",
        "gate-monitor-decision",
    ):
        assert f'id="{field_id}"'.encode() in response.data
    assert b"<button" not in response.data

    state_response = client.get("/api/live-state")
    state = state_response.get_json()
    assert state_response.status_code == 200
    assert state["gate"]["state"] == "LOCKED"
    assert state["gate"]["mode"] == "SIMULATOR"
    assert state["camera_running"] is False
    assert state["worker"] is None
    assert state["decision"] is None

    print("Gate simulator monitoring route checks passed!")


if __name__ == "__main__":
    main()
