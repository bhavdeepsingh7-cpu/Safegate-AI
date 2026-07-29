"""Focused Flask route and active-configuration checks for system settings."""

import dashboard


def main() -> None:
    configuration = dashboard.get_active_configuration()

    assert configuration["model_path"] == str(dashboard.MODEL_PATH)
    assert configuration["camera_index"] == 0
    assert configuration["detection_confidence"] == 0.25
    assert configuration["iou_threshold"] == 0.45
    assert configuration["image_size"] == 640
    assert configuration["decision_history_size"] == 15
    assert configuration["grant_threshold"] == 10
    assert configuration["deny_threshold"] == 10
    assert configuration["flask_host"] == "127.0.0.1"
    assert configuration["flask_port"] == 5000

    dashboard.app.config["TESTING"] = True
    response = dashboard.app.test_client().get("/settings")

    assert response.status_code == 200
    assert b"Active software configuration" in response.data
    assert b"This page is read-only." in response.data
    assert b"Arduino Nano integration" in response.data
    assert b"RFID identification" in response.data
    assert b'id="settings-camera-status"' in response.data
    assert b'id="settings-gate-state"' in response.data
    assert b"<button" not in response.data

    print("System settings route checks passed!")


if __name__ == "__main__":
    main()
