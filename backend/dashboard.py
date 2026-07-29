import csv
import re
from collections import Counter
from pathlib import Path

from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

from event_logger import EventLogger
from detector import INFERENCE_IMAGE_SIZE, INFERENCE_IOU_THRESHOLD
from live_feed import LiveFeedService
from snapshot_manager import SnapshotManager
from worker_db import Worker, WorkerDatabase


BASE_FOLDER = Path(__file__).resolve().parent.parent
FRONTEND_FOLDER = BASE_FOLDER / "frontend"
LOG_PATH = BASE_FOLDER / "logs" / "access_events.csv"
SNAPSHOT_ROOT = BASE_FOLDER / "logs" / "snapshots"
MODEL_PATH = (
    BASE_FOLDER
    / "runs"
    / "detect"
    / "runs"
    / "safegate_ppe"
    / "weights"
    / "best.pt"
)
DETECTION_CONFIDENCE = 0.25
CAMERA_INDEX = 0
DECISION_HISTORY_SIZE = 15
GRANT_THRESHOLD = 10
DENY_THRESHOLD = 10
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5000

app = Flask(
    __name__,
    template_folder=str(FRONTEND_FOLDER / "templates"),
    static_folder=str(FRONTEND_FOLDER / "static"),
)

worker_database = WorkerDatabase(
    database_path=str(BASE_FOLDER / "data" / "safegate.db")
)
event_logger = EventLogger(log_path=str(LOG_PATH))
snapshot_manager = SnapshotManager(base_folder=str(SNAPSHOT_ROOT))


def record_final_decision(
    worker: Worker,
    decision,
    display_frame,
) -> None:
    """Persist exactly one completed dashboard verification session."""

    snapshot_path = ""

    if decision.status in {"ACCESS DENIED", "MANAGER REVIEW"}:
        snapshot_path = snapshot_manager.save(
            display_frame,
            worker,
            decision,
        )

    event_logger.log(
        worker=worker,
        decision=decision,
        snapshot_path=snapshot_path,
    )


live_feed_service = LiveFeedService(
    model_path=str(MODEL_PATH),
    confidence=DETECTION_CONFIDENCE,
    camera_index=CAMERA_INDEX,
    on_final_decision=record_final_decision,
    decision_history_size=DECISION_HISTORY_SIZE,
    grant_threshold=GRANT_THRESHOLD,
    deny_threshold=DENY_THRESHOLD,
)


def get_active_configuration() -> dict[str, object]:
    """Return the values currently used by the local dashboard service."""

    return {
        "model_path": str(live_feed_service.model_path),
        "camera_index": live_feed_service.camera_index,
        "detection_confidence": live_feed_service.confidence,
        "iou_threshold": INFERENCE_IOU_THRESHOLD,
        "image_size": INFERENCE_IMAGE_SIZE,
        "decision_history_size": live_feed_service.decision_history_size,
        "grant_threshold": live_feed_service.grant_threshold,
        "deny_threshold": live_feed_service.deny_threshold,
        "database_path": str(worker_database.database_path),
        "log_path": str(LOG_PATH),
        "snapshot_folder": str(SNAPSHOT_ROOT),
        "flask_host": FLASK_HOST,
        "flask_port": FLASK_PORT,
    }


def build_snapshot_url(snapshot_path: str) -> str:
    if not snapshot_path:
        return ""

    snapshot = Path(snapshot_path)

    if not snapshot.is_absolute():
        snapshot = BASE_FOLDER / snapshot

    try:
        relative_path = snapshot.resolve().relative_to(
            SNAPSHOT_ROOT.resolve()
        )
    except ValueError:
        return ""

    return url_for("snapshot_file", filename=str(relative_path))


def load_events(log_path: Path | None = None) -> list[dict]:
    """Load recorded audit events, newest first."""

    source_path = log_path or LOG_PATH

    if not source_path.exists():
        return []

    with source_path.open("r", newline="", encoding="utf-8") as file:
        events = list(csv.DictReader(file))

    for event_index, event in enumerate(events):
        event["event_index"] = event_index
        event["snapshot_url"] = build_snapshot_url(
            event.get("snapshot_path", "")
        )

    events.reverse()
    return events


def calculate_statistics(events: list[dict]) -> dict:
    return {
        "total": len(events),
        "granted": sum(
            event.get("status") == "ACCESS GRANTED" for event in events
        ),
        "denied": sum(
            event.get("status") == "ACCESS DENIED" for event in events
        ),
        "review": sum(
            event.get("status") == "MANAGER REVIEW" for event in events
        ),
    }


def extract_missing_ppe_categories(reason: str) -> list[str]:
    """Extract explicitly recorded missing PPE names from a decision reason."""

    missing_list = re.search(
        r"Required PPE missing:\s*(.+?)(?:\.|$)",
        reason,
        flags=re.IGNORECASE,
    )
    if missing_list:
        return [
            category.strip().lower()
            for category in missing_list.group(1).split(",")
            if category.strip()
        ]

    missing_item = re.search(
        r"(?:required )?(?:hi-vis )?([a-z-]+) is missing",
        reason,
        flags=re.IGNORECASE,
    )
    return [missing_item.group(1).lower()] if missing_item else []


def calculate_report_analytics(events: list[dict]) -> dict:
    """Summarise only the decisions and human actions stored in the CSV log."""

    statistics = calculate_statistics(events)
    missing_ppe = Counter()
    worker_concerns: dict[str, dict] = {}

    for event in events:
        missing_ppe.update(
            extract_missing_ppe_categories(event.get("reason", ""))
        )

        if event.get("status") not in {"ACCESS DENIED", "MANAGER REVIEW"}:
            continue

        worker_id = event.get("worker_id") or "Unknown worker"
        concern = worker_concerns.setdefault(
            worker_id,
            {
                "worker_id": worker_id,
                "worker_name": event.get("worker_name") or "Unknown worker",
                "denied": 0,
                "review": 0,
                "total": 0,
            },
        )
        concern["total"] += 1
        if event.get("status") == "ACCESS DENIED":
            concern["denied"] += 1
        else:
            concern["review"] += 1

    def recorded_review_status(event: dict) -> str:
        return event.get("review_status") or event.get(
            "override_status", ""
        )

    total = statistics["total"]
    compliance_percentage = (
        round((statistics["granted"] / total) * 100, 1)
        if total
        else None
    )
    common_ppe = sorted(
        missing_ppe.items(),
        key=lambda item: (-item[1], item[0]),
    )
    concerns = sorted(
        worker_concerns.values(),
        key=lambda concern: (-concern["total"], concern["worker_name"]),
    )

    return {
        **statistics,
        "human_overrides": sum(
            recorded_review_status(event) == "OVERRIDDEN"
            for event in events
        ),
        "denial_confirmations": sum(
            recorded_review_status(event) == "DENIAL_CONFIRMED"
            for event in events
        ),
        "compliance_percentage": compliance_percentage,
        "most_common_missing_ppe": common_ppe[0][0] if common_ppe else None,
        "most_common_missing_ppe_count": common_ppe[0][1] if common_ppe else 0,
        "worker_concerns": concerns,
    }


def render_workers_page(
    search_query: str = "",
    editing_worker: Worker | None = None,
):
    """Render the worker-management page with an optional search or edit."""

    workers = (
        worker_database.search_workers(search_query)
        if search_query
        else worker_database.list_workers()
    )

    return render_template(
        "workers.html",
        page="workers",
        workers=workers,
        search_query=search_query,
        editing_worker=editing_worker,
        message=request.args.get("message", ""),
        message_type=request.args.get("message_type", "success"),
    )


def workers_redirect(
    message: str,
    message_type: str = "success",
):
    """Redirect to worker management with a user-facing result message."""

    return redirect(
        url_for(
            "workers_page",
            message=message,
            message_type=message_type,
        )
    )


def logs_redirect(
    message: str,
    message_type: str = "success",
):
    """Redirect to access logs with a user-facing result message."""

    return redirect(
        url_for(
            "logs_page",
            message=message,
            message_type=message_type,
        )
    )


def worker_from_form(worker_id: str) -> Worker | None:
    """Validate form values and create a worker record for add or edit."""

    name = request.form.get("name", "").strip()
    role = request.form.get("role", "").strip()

    if not worker_id or not name or not role:
        return None

    return Worker(
        worker_id=worker_id,
        name=name,
        role=role,
        helmet_exempt=request.form.get("helmet_exempt") == "on",
        active=request.form.get("active") == "on",
        notes=request.form.get("notes", "").strip(),
    )


def worker_is_in_active_session(worker_id: str) -> bool:
    """Return whether the live verification session currently uses this worker."""

    current_worker = live_feed_service.get_live_state().get("worker")
    return bool(
        current_worker
        and current_worker.get("worker_id") == worker_id
    )


@app.route("/")
def dashboard():
    events = load_events()

    return render_template(
        "dashboard.html",
        page="dashboard",
        events=events,
        statistics=calculate_statistics(events),
        workers=worker_database.list_workers(),
    )


@app.route("/workers")
def workers_page():
    return render_workers_page(
        search_query=request.args.get("search", "").strip()
    )


@app.route("/workers", methods=["POST"])
def add_worker():
    worker = worker_from_form(
        request.form.get("worker_id", "").strip()
    )

    if worker is None:
        return workers_redirect(
            "Worker ID, name, and role are required.",
            "error",
        )

    if not worker_database.add_worker(worker):
        return workers_redirect(
            f"Worker ID {worker.worker_id} already exists.",
            "error",
        )

    return workers_redirect(f"Added worker {worker.name}.")


@app.route("/workers/<worker_id>/edit")
def edit_worker_page(worker_id: str):
    worker = worker_database.get_worker(worker_id)

    if worker is None:
        return workers_redirect("Worker record was not found.", "error")

    return render_workers_page(editing_worker=worker)


@app.route("/workers/<worker_id>/edit", methods=["POST"])
def update_worker(worker_id: str):
    if worker_database.get_worker(worker_id) is None:
        return workers_redirect("Worker record was not found.", "error")

    worker = worker_from_form(worker_id)

    if worker is None:
        return workers_redirect(
            "Worker name and role are required.",
            "error",
        )

    if not worker_database.update_worker(worker):
        return workers_redirect("Worker record could not be updated.", "error")

    return workers_redirect(f"Updated worker {worker.name}.")


@app.route("/workers/<worker_id>/status", methods=["POST"])
def set_worker_status(worker_id: str):
    active = request.form.get("active") == "true"

    if not worker_database.set_worker_active(worker_id, active):
        return workers_redirect("Worker record was not found.", "error")

    status = "activated" if active else "deactivated"
    return workers_redirect(f"Worker {worker_id} {status}.")


@app.route("/workers/<worker_id>/delete", methods=["POST"])
def delete_worker(worker_id: str):
    if worker_is_in_active_session(worker_id):
        return workers_redirect(
            "Clear the active verification session before deleting this worker.",
            "error",
        )

    if not worker_database.delete_worker(worker_id):
        return workers_redirect("Worker record was not found.", "error")

    return workers_redirect(f"Deleted worker {worker_id}.")


@app.route("/logs")
def logs_page():
    events = load_events()
    review_events = [
        event
        for event in events
        if (
            event.get("status") in {"ACCESS DENIED", "MANAGER REVIEW"}
            and event.get("review_status") == "PENDING"
        )
    ]
    return render_template(
        "logs.html",
        page="logs",
        events=events,
        review_events=review_events,
        message=request.args.get("message", ""),
        message_type=request.args.get("message_type", "success"),
    )


@app.route("/logs/<int:event_index>/override", methods=["POST"])
def approve_override(event_index: int):
    manager_name = request.form.get("manager_name", "").strip()
    manager_reason = request.form.get("manager_reason", "").strip()

    if not manager_name or not manager_reason:
        return logs_redirect(
            "Manager name and reason are required.",
            "error",
        )

    if not event_logger.record_manager_action(
        event_index=event_index,
        manager_name=manager_name,
        manager_reason=manager_reason,
        review_status="OVERRIDDEN",
    ):
        return logs_redirect(
            "This event cannot be resolved or has already been reviewed.",
            "error",
        )

    return logs_redirect(
        "Human override recorded. The automated decision remains unchanged."
    )


@app.route("/logs/<int:event_index>/confirm-denial", methods=["POST"])
def confirm_denial(event_index: int):
    manager_name = request.form.get("manager_name", "").strip()
    manager_reason = request.form.get("manager_reason", "").strip()

    if not manager_name or not manager_reason:
        return logs_redirect("Manager name and reason are required.", "error")

    if not event_logger.record_manager_action(
        event_index=event_index,
        manager_name=manager_name,
        manager_reason=manager_reason,
        review_status="DENIAL_CONFIRMED",
    ):
        return logs_redirect(
            "This event cannot be resolved or has already been reviewed.",
            "error",
        )

    return logs_redirect(
        "Denial confirmation recorded. The automated decision remains unchanged."
    )


@app.route("/reports")
def reports_page():
    events = load_events()
    return render_template(
        "reports.html",
        page="reports",
        analytics=calculate_report_analytics(events),
        recent_events=events[:10],
    )


@app.route("/gate")
def gate_page():
    return render_template(
        "gate.html",
        page="gate",
    )


@app.route("/settings")
def settings_page():
    return render_template(
        "settings.html",
        page="settings",
        configuration=get_active_configuration(),
    )


@app.route("/snapshots/<path:filename>")
def snapshot_file(filename):
    return send_from_directory(SNAPSHOT_ROOT.resolve(), filename)


@app.route("/video-feed")
def video_feed():
    return Response(
        live_feed_service.generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/api/live-state")
def live_state():
    return jsonify(live_feed_service.get_live_state())


@app.route("/api/session", methods=["POST"])
def start_session():
    payload = request.get_json(silent=True) or request.form
    worker_id = str(payload.get("worker_id", "")).strip()
    worker = worker_database.get_worker(worker_id)

    if worker is None:
        return jsonify({"success": False, "message": "Worker ID was not found."}), 404

    if not worker.active:
        return jsonify({"success": False, "message": "This worker is inactive."}), 403

    live_feed_service.select_worker(worker)
    live_feed_service.start()

    return jsonify(
        {
            "success": True,
            "message": f"Verification started for {worker.name}.",
            "state": live_feed_service.get_live_state(),
        }
    )


@app.route("/api/session/clear", methods=["POST"])
def clear_session():
    live_feed_service.clear_worker()
    return jsonify({"success": True, "message": "Verification session cleared."})


@app.route("/camera/start", methods=["POST"])
def start_camera():
    live_feed_service.start()
    return jsonify({"success": True, **live_feed_service.get_live_state()})


@app.route("/camera/stop", methods=["POST"])
def stop_camera():
    live_feed_service.stop()
    return jsonify({"success": True, **live_feed_service.get_live_state()})


@app.route("/camera/status")
def camera_status():
    return jsonify(live_feed_service.get_live_state())


if __name__ == "__main__":
    print("SafeGate AI dashboard starting...")
    print("Open http://127.0.0.1:5000")
    app.run(
        host=FLASK_HOST,
        port=FLASK_PORT,
        debug=False,
        use_reloader=False,
    )
