import csv
from pathlib import Path

from flask import (
    Flask,
    Response,
    jsonify,
    render_template,
    send_from_directory,
    url_for,
)

from live_feed import LiveFeedService
from worker_db import WorkerDatabase

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

app = Flask(
    __name__,
    template_folder=str(
        FRONTEND_FOLDER / "templates"
    ),
    static_folder=str(
        FRONTEND_FOLDER / "static"
    ),
)

worker_database = WorkerDatabase(
    database_path=str(
        BASE_FOLDER / "data" / "safegate.db"
    )
)

MODEL_PATH = (
    BASE_FOLDER
    / "runs"
    / "detect"
    / "runs"
    / "safegate_ppe"
    / "weights"
    / "best.pt"
)

live_feed_service = LiveFeedService(
    model_path=str(MODEL_PATH),
    confidence=0.25,
    camera_index=0,
)


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

    return url_for(
        "snapshot_file",
        filename=str(relative_path),
    )


def load_events() -> list[dict]:
    if not LOG_PATH.exists():
        return []

    with LOG_PATH.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        events = list(csv.DictReader(file))

    for event in events:
        event["snapshot_url"] = build_snapshot_url(
            event.get("snapshot_path", "")
        )

    events.reverse()

    return events


def calculate_statistics(events: list[dict]) -> dict:
    return {
        "total": len(events),
        "granted": sum(
            event.get("status") == "ACCESS GRANTED"
            for event in events
        ),
        "denied": sum(
            event.get("status") == "ACCESS DENIED"
            for event in events
        ),
        "review": sum(
            event.get("status") == "MANAGER REVIEW"
            for event in events
        ),
    }


@app.route("/")
def dashboard():
    events = load_events()
    statistics = calculate_statistics(events)

    return render_template(
        "dashboard.html",
        page="dashboard",
        events=events,
        statistics=statistics,
    )


@app.route("/workers")
def workers_page():
    workers = worker_database.list_workers()

    return render_template(
        "placeholder.html",
        page="workers",
        heading="Worker Management",
        description=(
            "Add, edit, search and manage registered workers."
        ),
        workers=workers,
    )


@app.route("/logs")
def logs_page():
    return render_template(
        "placeholder.html",
        page="logs",
        heading="Access Logs",
        description=(
            "Search access decisions, evidence and overrides."
        ),
    )


@app.route("/reports")
def reports_page():
    return render_template(
        "placeholder.html",
        page="reports",
        heading="Reports and Analytics",
        description=(
            "Review site-entry trends and PPE violations."
        ),
    )


@app.route("/gate")
def gate_page():
    return render_template(
        "placeholder.html",
        page="gate",
        heading="Gate Control",
        description=(
            "Monitor gate state and hardware connectivity."
        ),
    )


@app.route("/settings")
def settings_page():
    return render_template(
        "placeholder.html",
        page="settings",
        heading="System Settings",
        description=(
            "Configure detection and hardware preferences."
        ),
    )


@app.route("/snapshots/<path:filename>")
def snapshot_file(filename):
    return send_from_directory(
        SNAPSHOT_ROOT.resolve(),
        filename,
    )

@app.route("/video-feed")
def video_feed():
    return Response(
        live_feed_service.generate_frames(),
        mimetype=(
            "multipart/x-mixed-replace; "
            "boundary=frame"
        ),
    )
@app.route("/camera/start", methods=["POST"])
def start_camera():
    live_feed_service.start()

    return jsonify(
        {
            "success": True,
            "camera_running": live_feed_service.running,
            "message": "Camera started.",
        }
    )


@app.route("/camera/stop", methods=["POST"])
def stop_camera():
    live_feed_service.stop()

    return jsonify(
        {
            "success": True,
            "camera_running": live_feed_service.running,
            "message": "Camera stopped.",
        }
    )


@app.route("/camera/status")
def camera_status():
    return jsonify(
        {
            "camera_running": live_feed_service.running,
            "error": live_feed_service.error_message,
        }
    )

if __name__ == "__main__":
    print("SafeGate AI dashboard starting...")
    print("Open http://127.0.0.1:5000")

    app.run(
    host="127.0.0.1",
    port=5000,
    debug=False,
    use_reloader=False,
)