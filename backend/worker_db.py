import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Worker:
    worker_id: str
    name: str
    role: str
    helmet_exempt: bool
    active: bool
    notes: str = ""


class WorkerDatabase:
    """Stores and manages SafeGate worker records."""

    def __init__(self, database_path: str = "data/safegate.db"):
        self.database_path = Path(database_path)

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._create_table()
        self._add_demo_workers()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row

        return connection

    def _create_table(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS workers (
                    worker_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    helmet_exempt INTEGER NOT NULL DEFAULT 0,
                    active INTEGER NOT NULL DEFAULT 1,
                    notes TEXT NOT NULL DEFAULT ''
                )
                """
            )

    def _add_demo_workers(self) -> None:
        demo_workers = [
            Worker(
                worker_id="1001",
                name="Bhavdeep Singh",
                role="Electrician",
                helmet_exempt=True,
                active=True,
                notes="Approved Sikh safety-helmet exemption.",
            ),
            Worker(
                worker_id="1002",
                name="John Smith",
                role="Site Labourer",
                helmet_exempt=False,
                active=True,
                notes="Standard PPE requirements.",
            ),
            Worker(
                worker_id="1003",
                name="Amelia Jones",
                role="Site Visitor",
                helmet_exempt=False,
                active=False,
                notes="Access currently disabled.",
            ),
        ]

        for worker in demo_workers:
            self.add_worker(
                worker,
                ignore_existing=True,
            )

    def add_worker(
        self,
        worker: Worker,
        ignore_existing: bool = False,
    ) -> bool:
        """Add a new worker.

        Returns True when created and False when the ID already exists.
        """

        sql_command = (
            """
            INSERT OR IGNORE INTO workers (
                worker_id,
                name,
                role,
                helmet_exempt,
                active,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """
            if ignore_existing
            else
            """
            INSERT INTO workers (
                worker_id,
                name,
                role,
                helmet_exempt,
                active,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """
        )

        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    sql_command,
                    (
                        worker.worker_id,
                        worker.name,
                        worker.role,
                        int(worker.helmet_exempt),
                        int(worker.active),
                        worker.notes,
                    ),
                )

                return cursor.rowcount > 0

        except sqlite3.IntegrityError:
            return False

    def get_worker(
        self,
        worker_id: str,
    ) -> Optional[Worker]:
        """Find one worker by ID."""

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    worker_id,
                    name,
                    role,
                    helmet_exempt,
                    active,
                    notes
                FROM workers
                WHERE worker_id = ?
                """,
                (worker_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_worker(row)

    def list_workers(self) -> list[Worker]:
        """Return every worker ordered by ID."""

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    worker_id,
                    name,
                    role,
                    helmet_exempt,
                    active,
                    notes
                FROM workers
                ORDER BY worker_id
                """
            ).fetchall()

        return [
            self._row_to_worker(row)
            for row in rows
        ]

    def search_workers(
        self,
        search_text: str,
    ) -> list[Worker]:
        """Search workers by ID, name or role."""

        search_pattern = f"%{search_text.strip()}%"

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    worker_id,
                    name,
                    role,
                    helmet_exempt,
                    active,
                    notes
                FROM workers
                WHERE
                    worker_id LIKE ?
                    OR name LIKE ?
                    OR role LIKE ?
                ORDER BY worker_id
                """,
                (
                    search_pattern,
                    search_pattern,
                    search_pattern,
                ),
            ).fetchall()

        return [
            self._row_to_worker(row)
            for row in rows
        ]

    def update_worker(
        self,
        worker: Worker,
    ) -> bool:
        """Update an existing worker."""

        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE workers
                SET
                    name = ?,
                    role = ?,
                    helmet_exempt = ?,
                    active = ?,
                    notes = ?
                WHERE worker_id = ?
                """,
                (
                    worker.name,
                    worker.role,
                    int(worker.helmet_exempt),
                    int(worker.active),
                    worker.notes,
                    worker.worker_id,
                ),
            )

            return cursor.rowcount > 0

    def set_worker_active(
        self,
        worker_id: str,
        active: bool,
    ) -> bool:
        """Activate or deactivate a worker."""

        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE workers
                SET active = ?
                WHERE worker_id = ?
                """,
                (
                    int(active),
                    worker_id,
                ),
            )

            return cursor.rowcount > 0

    def delete_worker(
        self,
        worker_id: str,
    ) -> bool:
        """Permanently delete a worker."""

        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM workers
                WHERE worker_id = ?
                """,
                (worker_id,),
            )

            return cursor.rowcount > 0

    @staticmethod
    def _row_to_worker(
        row: sqlite3.Row,
    ) -> Worker:
        return Worker(
            worker_id=row["worker_id"],
            name=row["name"],
            role=row["role"],
            helmet_exempt=bool(
                row["helmet_exempt"]
            ),
            active=bool(row["active"]),
            notes=row["notes"] or "",
        )