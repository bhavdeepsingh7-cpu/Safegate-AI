from pathlib import Path

from worker_db import Worker, WorkerDatabase


TEST_DATABASE = Path("data/test_worker_crud.db")


def remove_old_test_database() -> None:
    if TEST_DATABASE.exists():
        TEST_DATABASE.unlink()


def main():
    remove_old_test_database()

    database = WorkerDatabase(
        database_path=str(TEST_DATABASE)
    )

    print("\nTesting worker creation...")

    new_worker = Worker(
        worker_id="2001",
        name="Test Worker",
        role="Carpenter",
        helmet_exempt=False,
        active=True,
        notes="Created during CRUD testing.",
    )

    created = database.add_worker(new_worker)

    assert created is True

    saved_worker = database.get_worker("2001")

    assert saved_worker is not None
    assert saved_worker.name == "Test Worker"

    print("Create worker test passed.")

    print("\nTesting duplicate worker protection...")

    duplicate_created = database.add_worker(new_worker)

    assert duplicate_created is False

    print("Duplicate protection test passed.")

    print("\nTesting worker update...")

    updated_worker = Worker(
        worker_id="2001",
        name="Updated Worker",
        role="Senior Carpenter",
        helmet_exempt=True,
        active=True,
        notes="Worker record was updated.",
    )

    updated = database.update_worker(updated_worker)

    assert updated is True

    saved_worker = database.get_worker("2001")

    assert saved_worker is not None
    assert saved_worker.name == "Updated Worker"
    assert saved_worker.role == "Senior Carpenter"
    assert saved_worker.helmet_exempt is True

    print("Update worker test passed.")

    print("\nTesting worker search...")

    search_results = database.search_workers(
        "Carpenter"
    )

    assert any(
        worker.worker_id == "2001"
        for worker in search_results
    )

    print("Worker search test passed.")

    print("\nTesting worker deactivation...")

    deactivated = database.set_worker_active(
        worker_id="2001",
        active=False,
    )

    assert deactivated is True

    saved_worker = database.get_worker("2001")

    assert saved_worker is not None
    assert saved_worker.active is False

    print("Worker deactivation test passed.")

    print("\nTesting worker reactivation...")

    reactivated = database.set_worker_active(
        worker_id="2001",
        active=True,
    )

    assert reactivated is True

    saved_worker = database.get_worker("2001")

    assert saved_worker is not None
    assert saved_worker.active is True

    print("Worker reactivation test passed.")

    print("\nTesting worker deletion...")

    deleted = database.delete_worker("2001")

    assert deleted is True
    assert database.get_worker("2001") is None

    print("Delete worker test passed.")

    remove_old_test_database()

    print(
        "\nAll worker CRUD tests passed!\n"
    )


if __name__ == "__main__":
    main()