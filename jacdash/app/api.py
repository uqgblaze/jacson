"""
app/api.py — All /api/* endpoints for JacDash.

Every endpoint enforces authentication via @require_auth.
"""

import os
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, send_file, abort
import pytz

import db
import config
from app.auth import require_auth, get_remote_user
from app.runner import start_job, _calc_next_run

api_bp = Blueprint("api", __name__)

BRISBANE_TZ = pytz.timezone("Australia/Brisbane")


# ── Dashboard summary ──────────────────────────────────────────────────────────

@api_bp.route("/dashboard")
@require_auth
def dashboard():
    """
    Returns everything the frontend needs to render the dashboard:
    server time, next scheduled run, current job state, courses count.
    """
    now_bne = datetime.now(BRISBANE_TZ)
    state = db.get_job_state()
    settings = db.get_settings()
    courses_count = db.count_courses()

    return jsonify({
        "server_time": now_bne.strftime("%a, %d %b %Y  %H:%M:%S AEST"),
        "next_run_at": state.get("next_run_at"),
        "job_state": {
            "status": state.get("status", "idle"),
            "is_scheduled": bool(state.get("is_scheduled")),
            "current_job_id": state.get("current_job_id"),
            "started_at": state.get("started_at"),
            "finished_at": state.get("finished_at"),
            "courses_scraped": state.get("courses_scraped"),
            "courses_skipped": state.get("courses_skipped"),
        },
        "schedule": {
            "time": settings.get("schedule_time"),
            "days": settings.get("schedule_days"),
        },
        "courses_count": courses_count,
        "username": get_remote_user(),
    })


# ── Manual run ─────────────────────────────────────────────────────────────────

@api_bp.route("/run", methods=["POST"])
@require_auth
def run():
    """Start a manual JacSON run. Returns 409 if already running."""
    username = get_remote_user()
    try:
        result = start_job(triggered_by=username, is_scheduled=False)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 409
    return jsonify({"job_id": result["job_id"]}), 202


# ── Log streaming ──────────────────────────────────────────────────────────────

@api_bp.route("/log")
@require_auth
def log():
    """
    Return log lines for a given job_id.

    Query params:
      job_id    — required
      offset    — byte offset to read from (default 0); use next_offset for polling
      download  — if '1', serve the file as an attachment
    """
    job_id = request.args.get("job_id", "").strip()
    if not job_id:
        return jsonify({"error": "job_id is required"}), 400

    # Security: job_id must be a safe timestamp string
    import re
    if not re.fullmatch(r"\d{8}_\d{6}", job_id):
        abort(400)

    log_path = os.path.join(config.LOGS_DIR, f"scrape_{job_id}.log")
    if not os.path.exists(log_path):
        return jsonify({"lines": "", "next_offset": 0, "is_running": False})

    if request.args.get("download") == "1":
        return send_file(
            log_path,
            as_attachment=True,
            download_name=f"jacdash_{job_id}.log",
            mimetype="text/plain",
        )

    offset = int(request.args.get("offset", 0))
    state = db.get_job_state()
    is_running = (
        state.get("status") == "running"
        and state.get("current_job_id") == job_id
    )

    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            f.seek(offset)
            chunk = f.read(65536)  # max 64 KB per poll
            next_offset = f.tell()
    except OSError:
        return jsonify({"lines": "", "next_offset": offset, "is_running": is_running})

    return jsonify({
        "lines": chunk,
        "next_offset": next_offset,
        "is_running": is_running,
    })


# ── Schedule ───────────────────────────────────────────────────────────────────

@api_bp.route("/schedule", methods=["GET", "POST"])
@require_auth
def schedule():
    if request.method == "GET":
        settings = db.get_settings()
        state = db.get_job_state()
        return jsonify({
            "time": settings.get("schedule_time"),
            "days": settings.get("schedule_days"),
            "next_run_at": state.get("next_run_at"),
        })

    data = request.get_json(force=True)
    schedule_time = data.get("time", "").strip()
    schedule_days = data.get("days", "").strip()

    # Basic validation
    import re
    if not re.fullmatch(r"\d{2}:\d{2}", schedule_time):
        return jsonify({"error": "Invalid time format. Use HH:MM"}), 400

    valid_days = {"Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"}
    day_list = [d.strip().capitalize()[:3] for d in schedule_days.split(",") if d.strip()]
    if not all(d in valid_days for d in day_list):
        return jsonify({"error": "Invalid days. Use Mon,Tue,...,Sun"}), 400

    canonical_days = ",".join(day_list)
    next_run_at = _calc_next_run_with(schedule_time, canonical_days)

    db.save_settings(schedule_time, canonical_days, next_run_at=next_run_at)
    # Also update job_state.next_run_at immediately
    import sqlite3
    with db.get_db() as conn:
        conn.execute(
            "UPDATE job_state SET next_run_at = ? WHERE id = 1",
            (next_run_at,)
        )

    return jsonify({
        "time": schedule_time,
        "days": canonical_days,
        "next_run_at": next_run_at,
    })


def _calc_next_run_with(schedule_time: str, schedule_days: str) -> str | None:
    """Calculate next_run_at for an arbitrary time/days combination."""
    from datetime import timedelta

    day_map = {
        "mon": 0, "tue": 1, "wed": 2, "thu": 3,
        "fri": 4, "sat": 5, "sun": 6,
    }
    wanted_days = {
        day_map[d.strip().lower()]
        for d in schedule_days.split(",")
        if d.strip().lower() in day_map
    }
    if not wanted_days:
        return None

    now = datetime.now(BRISBANE_TZ)
    h, m = (int(x) for x in schedule_time.split(":"))

    for offset in range(1, 8):
        candidate = now + timedelta(days=offset)
        if candidate.weekday() in wanted_days:
            next_dt = candidate.replace(hour=h, minute=m, second=0, microsecond=0)
            return next_dt.isoformat()

    return None


# ── Users ──────────────────────────────────────────────────────────────────────

@api_bp.route("/users", methods=["GET"])
@require_auth
def list_users():
    return jsonify(db.get_users())


@api_bp.route("/users", methods=["POST"])
@require_auth
def add_user():
    data = request.get_json(force=True)
    username = (data.get("uq_username") or "").strip().lower()
    full_name = (data.get("full_name") or "").strip()

    if not username or not full_name:
        return jsonify({"error": "uq_username and full_name are required"}), 400

    import re
    if not re.fullmatch(r"[a-z0-9]{3,20}", username):
        return jsonify({"error": "Invalid UQ username format"}), 400

    try:
        db.add_user(username, full_name)
    except Exception as exc:
        if "UNIQUE" in str(exc):
            return jsonify({"error": f"{username} is already a JacDash user"}), 409
        raise

    return jsonify({"uq_username": username, "full_name": full_name}), 201


@api_bp.route("/users/<uq_username>", methods=["DELETE"])
@require_auth
def delete_user(uq_username: str):
    current = get_remote_user()
    if uq_username == current:
        return jsonify({"error": "You cannot remove yourself"}), 400
    db.remove_user(uq_username)
    return "", 204
