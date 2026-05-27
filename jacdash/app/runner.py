"""
app/runner.py — Subprocess launch and job lifecycle management for JacDash.

start_job() is called both from the /api/run endpoint (manual)
and from cron_scheduler.py (scheduled).
"""

import os
import sys
import threading
import subprocess
import logging
from datetime import datetime

import config
import db

log = logging.getLogger("jacdash.runner")


def start_job(triggered_by: str, is_scheduled: bool = False) -> dict:
    """
    Start a JacSON scraper run in a background subprocess.

    Parameters
    ----------
    triggered_by  : UQ username string, or "scheduled"
    is_scheduled  : True when triggered by cron_scheduler

    Returns
    -------
    dict with job_id on success, or raises RuntimeError if already running.
    """
    state = db.get_job_state()
    if state.get("status") == "running":
        raise RuntimeError("A job is already running.")

    job_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(config.LOGS_DIR, f"scrape_{job_id}.log")
    os.makedirs(config.LOGS_DIR, exist_ok=True)

    # Determine Python executable (venv if present)
    venv_python = os.path.join(config.JACDASH_ROOT, "..", "venv", "bin", "python")
    python_exe = venv_python if os.path.exists(venv_python) else sys.executable

    cmd = [python_exe, config.RUN_JACSON, "--job-id", job_id]

    db.set_job_running(job_id, is_scheduled)

    log_file = open(log_path, "w", encoding="utf-8", buffering=1)
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=config.JACSON_ROOT,
        )
    except Exception as exc:
        log_file.close()
        db.set_job_finished(job_id, "failed", 0, 0)
        db.append_job_history({
            "job_id": job_id,
            "triggered_by": triggered_by,
            "is_scheduled": is_scheduled,
            "started_at": datetime.utcnow().isoformat(),
            "finished_at": datetime.utcnow().isoformat(),
            "status": "failed",
            "courses_scraped": 0,
            "courses_skipped": 0,
            "log_path": log_path,
            "error": str(exc),
        })
        raise

    # Monitor in a daemon thread so Flask stays responsive
    thread = threading.Thread(
        target=_monitor,
        args=(proc, log_file, job_id, triggered_by, is_scheduled, log_path),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id, "log_path": log_path}


def _monitor(proc, log_file, job_id, triggered_by, is_scheduled, log_path):
    """Wait for the subprocess to finish, then update DB and job history."""
    started_at = datetime.utcnow().isoformat()
    proc.wait()
    log_file.close()

    finished_at = datetime.utcnow().isoformat()
    exit_code = proc.returncode
    status = "success" if exit_code == 0 else "failed"

    scraped, skipped = _parse_counts(log_path)

    # Recalculate next_run_at from current schedule
    next_run_at = _calc_next_run()

    db.set_job_finished(job_id, status, scraped, skipped, next_run_at)
    db.append_job_history({
        "job_id": job_id,
        "triggered_by": triggered_by,
        "is_scheduled": is_scheduled,
        "started_at": started_at,
        "finished_at": finished_at,
        "status": status,
        "courses_scraped": scraped,
        "courses_skipped": skipped,
        "log_path": log_path,
    })
    log.info("Job %s finished with status=%s", job_id, status)


def _parse_counts(log_path: str) -> tuple[int, int]:
    """
    Read the log file and extract courses_scraped / courses_skipped counts.
    jacson.py logs: "Loaded N included / M excluded courses"
    Returns (scraped, skipped).
    """
    import re
    scraped = skipped = 0
    if not os.path.exists(log_path):
        return scraped, skipped
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                m = re.search(
                    r"Loaded\s+(\d+)\s+included\s*/\s*(\d+)\s+excluded", line
                )
                if m:
                    scraped = int(m.group(1))
                    skipped = int(m.group(2))
    except OSError:
        pass
    return scraped, skipped


def _calc_next_run() -> str | None:
    """Calculate the next scheduled run datetime from DB settings."""
    from datetime import timedelta
    import pytz

    settings = db.get_settings()
    schedule_time = settings.get("schedule_time", "03:00")
    schedule_days = settings.get("schedule_days", "")

    if not schedule_days:
        return None

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

    try:
        tz = pytz.timezone("Australia/Brisbane")
    except Exception:
        tz = pytz.utc

    now = datetime.now(tz)
    h, m = (int(x) for x in schedule_time.split(":"))

    for offset in range(1, 8):
        candidate = now + timedelta(days=offset)
        if candidate.weekday() in wanted_days:
            next_dt = candidate.replace(hour=h, minute=m, second=0, microsecond=0)
            return next_dt.isoformat()

    return None
