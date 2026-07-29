from decision_engine import DecisionEngine
from event_logger import EventLogger
from snapshot_manager import SnapshotManager
from violation_tracker import ViolationTracker
from worker_db import WorkerDatabase


def test_worker_database():
    database = WorkerDatabase()

    exempt_worker = database.get_worker("1001")
    standard_worker = database.get_worker("1002")
    inactive_worker = database.get_worker("1003")

    assert exempt_worker is not None
    assert exempt_worker.helmet_exempt is True
    assert exempt_worker.active is True

    assert standard_worker is not None
    assert standard_worker.helmet_exempt is False
    assert standard_worker.active is True

    assert inactive_worker is not None
    assert inactive_worker.active is False

    print("Worker database test passed.")


def test_standard_access_granted():
    engine = DecisionEngine(
        history_size=15,
        grant_threshold=10,
        deny_threshold=10,
        helmet_required=True,
    )

    for _ in range(15):
        decision = engine.update(["helmet", "vest"])

    assert decision.status == "ACCESS GRANTED"

    print("Standard access-granted test passed.")


def test_standard_access_denied():
    engine = DecisionEngine(
        history_size=15,
        grant_threshold=10,
        deny_threshold=10,
        helmet_required=True,
    )

    for _ in range(15):
        decision = engine.update(
            ["Person", "no_helmet", "vest"]
        )

    assert decision.status == "ACCESS DENIED"

    print("Standard access-denied test passed.")


def test_exemption_access_granted():
    engine = DecisionEngine(
        history_size=15,
        grant_threshold=10,
        deny_threshold=10,
        helmet_required=False,
    )

    for _ in range(15):
        decision = engine.update(["vest", "no_helmet"])

    assert decision.status == "ACCESS GRANTED"

    print("Helmet-exemption route test passed.")


def test_exemption_denied_without_vest():
    engine = DecisionEngine(
        history_size=15,
        grant_threshold=10,
        deny_threshold=10,
        helmet_required=False,
    )

    for _ in range(15):
        decision = engine.update(
            ["Person", "no_helmet", "no_vest"]
        )

    assert decision.status == "ACCESS DENIED"

    print("Exemption missing-vest test passed.")


def test_manager_review():
    engine = DecisionEngine(
        history_size=15,
        grant_threshold=10,
        deny_threshold=10,
        helmet_required=True,
    )

    for frame_number in range(15):
        if frame_number % 2 == 0:
            classes = ["helmet", "vest"]
        else:
            classes = ["Person"]

        decision = engine.update(classes)

    assert decision.status == "MANAGER REVIEW"

    print("Manager-review test passed.")


def test_supporting_modules():
    EventLogger(
        log_path="logs/test_access_events.csv"
    )

    SnapshotManager(
        base_folder="logs/test_snapshots"
    )

    tracker = ViolationTracker(
        log_path="logs/test_access_events.csv",
        warning_threshold=3,
    )

    assert tracker.count_violations("1002") == 0

    print("Logger, snapshot and violation modules loaded.")


def main():
    print("\nRunning SafeGate AI system tests...\n")

    test_worker_database()
    test_standard_access_granted()
    test_standard_access_denied()
    test_exemption_access_granted()
    test_exemption_denied_without_vest()
    test_manager_review()
    test_supporting_modules()

    print("\nAll SafeGate AI system tests passed!\n")


if __name__ == "__main__":
    main()