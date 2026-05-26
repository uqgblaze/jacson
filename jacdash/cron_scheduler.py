#!/usr/bin/env python3
"""
cron_scheduler.py — JacDash scheduled-run trigger.

Called every minute by the OS cron job:
    * * * * * /path/to/venv/bin/python /home/uqgblaze/jacdash/cron_scheduler.py \
              >> /home/uqgblaze/jacdash/logs/cron.log 2>&1

It checks whether the current Brisbane time matches the saved schedule,
and if so (and no job is already running) it starts a scheduled JacSON run.
"""

import sys
import os
import logging
from datetime import datetime

# Ensure the jacdash package root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytz
import config
import db
from app.runner import start_job

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [cron] %(levelname)s: %(message)s",
)
log = logging.getLogger("jacdash.cron")


def should_run_now(schedule_time: str, schedule_days: str) -> bool:
    """
    Return True if the current Brisbane time matches the schedule.
    Matches on HH:MM and weekday name (Mon, Tue, ...).
    """
    if not schedule_time or not schedule_days:
        return False

    try:
        tz = pytz.timezone("Australia/Brisbane")
        now = datetime.now(tz)
    except Exception:
        now = datetime.utcnow()

    current_time = now.strftime("%H:%M")
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    current_day = day_names[now.weekday()]

    days_wanted = {d.strip() for d in schedule_days.split(",") if d.strip()}

    return (current_time == schedule_time) and (current_day in days_wanted)


def main():
    # Initialise DB (creates tables on first run)
    db.init_db()

    settings = db.get_settings()
    schedule_time = settings.get("schedule_time", "")
    schedule_days = settings.get("schedule_days", "")

    log.info("Checking schedule: time=%s days=%s", schedule_time, schedule_days)

    if not should_run_now(schedule_time, schedule_days):
        log.info("Not scheduled to run now. Exiting.")
        return

    state = db.get_job_state()
    if state.get("status") == "running":
        log.warning("Skipping scheduled run: a job is already running (%s).",
                    state.get("current_job_id"))
        return

    log.info("Starting scheduled JacSON run.")
    try:
        result = start_job(triggered_by="scheduled", is_scheduled=True)
        log.info("Scheduled job started: job_id=%s", result["job_id"])
    except Exception as exc:
        log.error("Failed to start scheduled job: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
