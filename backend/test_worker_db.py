from worker_db import WorkerDatabase


database = WorkerDatabase()

print("\nAll workers:\n")

for worker in database.list_workers():
    print(
        f"ID: {worker.worker_id} | "
        f"Name: {worker.name} | "
        f"Role: {worker.role} | "
        f"Helmet exempt: {worker.helmet_exempt} | "
        f"Active: {worker.active}"
    )


print("\nTesting worker lookup:\n")

worker = database.get_worker("1001")

assert worker is not None
assert worker.name == "Bhavdeep Singh"
assert worker.helmet_exempt is True
assert worker.active is True

print(worker)
print("\nWorker database test passed!")
