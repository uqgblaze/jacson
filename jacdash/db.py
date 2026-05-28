"""
db.py — SQLite helpers for JacDash.

Tables
------
users       — authorised UQ staff who can access JacDash
settings    — single-row global config (schedule, last job id)
job_state   — single-row current / most-recent job state
"""

import sqlite3
import json
import os
import hashlib
from datetime import datetime
from contextlib import contextmanager

import config


@contextmanager
def get_db():
    """Yield a sqlite3 connection with row_factory set to Row."""
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _parse_bootstrap_admin_user(raw_user: str):
    raw = (raw_user or "").strip()
    if not raw:
        return None, None
    if ":" in raw:
        username, full_name = raw.split(":", 1)
    else:
        username, full_name = raw, raw
    username = username.strip().lower()
    full_name = full_name.strip() or username
    return username, full_name


def init_db():
    """Create tables and seed bootstrap data if they don't exist yet."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                uq_username TEXT    UNIQUE NOT NULL,
                full_name   TEXT    NOT NULL,
                is_admin    INTEGER NOT NULL DEFAULT 0,
                is_active   INTEGER NOT NULL DEFAULT 1,
                created_at  TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bootstrap_admin_secrets (
                id                  INTEGER PRIMARY KEY CHECK (id = 1),
                username            TEXT NOT NULL,
                password_sha256     TEXT NOT NULL,
                created_at          TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS settings (
                id             INTEGER PRIMARY KEY CHECK (id = 1),
                schedule_time  TEXT NOT NULL,
                schedule_days  TEXT NOT NULL,
                last_job_id    TEXT
            );

            CREATE TABLE IF NOT EXISTS job_state (
                id              INTEGER PRIMARY KEY CHECK (id = 1),
                status          TEXT    NOT NULL DEFAULT 'idle',
                is_scheduled    INTEGER NOT NULL DEFAULT 0,
                current_job_id  TEXT,
                started_at      TEXT,
                finished_at     TEXT,
                courses_scraped INTEGER,
                courses_skipped INTEGER,
                next_run_at     TEXT
            );
        """)

        # Seed settings row
        conn.execute("""
            INSERT OR IGNORE INTO settings (id, schedule_time, schedule_days)
            VALUES (1, ?, ?)
        """, (config.DEFAULT_SCHEDULE_TIME, config.DEFAULT_SCHEDULE_DAYS))

        # Seed job_state row
        conn.execute("""
            INSERT OR IGNORE INTO job_state (id, status, is_scheduled)
            VALUES (1, 'idle', 0)
        """)

        # Backfill older DBs that predate admin/active columns
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()
        }
        if "is_admin" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
        if "is_active" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")

        # Ensure at least one active admin exists, optionally from env bootstrap vars
        admin_count = conn.execute(
            "SELECT COUNT(1) FROM users WHERE is_admin = 1 AND is_active = 1"
        ).fetchone()[0]
        bootstrap_ran = False
        bootstrap_message = "Bootstrap skipped: active admin already exists."

        if admin_count == 0:
            username, full_name = _parse_bootstrap_admin_user(config.BOOTSTRAP_ADMIN_USER)
            password = (config.BOOTSTRAP_ADMIN_PASSWORD or "").strip()
            if username and password:
                now = datetime.utcnow().isoformat()
                conn.execute("""
                    INSERT OR IGNORE INTO users
                    (uq_username, full_name, is_admin, is_active, created_at)
                    VALUES (?, ?, 1, 1, ?)
                """, (username, full_name, now))
                conn.execute("""
                    INSERT OR REPLACE INTO bootstrap_admin_secrets
                    (id, username, password_sha256, created_at)
                    VALUES (1, ?, ?, ?)
                """, (username, hashlib.sha256(password.encode("utf-8")).hexdigest(), now))
                bootstrap_ran = True
                bootstrap_message = (
                    f"Bootstrap admin created for '{username}'. "
                    "Treat credentials as one-time-use and rotate immediately."
                )
            else:
                bootstrap_message = (
                    "Bootstrap not run: no active admin exists and bootstrap env vars are missing. "
                    "Set JACDASH_BOOTSTRAP_ADMIN_USER and JACDASH_BOOTSTRAP_ADMIN_PASSWORD."
                )

    return {"bootstrap_ran": bootstrap_ran, "message": bootstrap_message}


# ── Users ──────────────────────────────────────────────────────────────────────

def get_users():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT uq_username, full_name, created_at FROM users ORDER BY full_name"
        ).fetchall()
    return [dict(r) for r in rows]


def user_exists(uq_username: str) -> bool:
    with get_db() as conn:
        row = conn.execute(
            "SELECT 1 FROM users WHERE uq_username = ? AND is_active = 1", (uq_username,)
        ).fetchone()
    return row is not None


def add_user(uq_username: str, full_name: str):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO users (uq_username, full_name, created_at) VALUES (?, ?, ?)",
            (uq_username.strip().lower(), full_name.strip(),
             datetime.utcnow().isoformat()),
        )


def remove_user(uq_username: str):
    with get_db() as conn:
        conn.execute("DELETE FROM users WHERE uq_username = ?", (uq_username,))


# ── Settings ───────────────────────────────────────────────────────────────────

def get_settings() -> dict:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM settings WHERE id = 1").fetchone()
    return dict(row) if row else {}


def save_settings(schedule_time: str, schedule_days: str,
                  next_run_at: str = None, last_job_id: str = None):
    with get_db() as conn:
        conn.execute("""
            UPDATE settings
            SET schedule_time = ?, schedule_days = ?
            WHERE id = 1
        """, (schedule_time, schedule_days))
        if last_job_id is not None:
            conn.execute(
                "UPDATE settings SET last_job_id = ? WHERE id = 1",
                (last_job_id,)
            )
    # next_run_at lives in job_state
    if next_run_at is not None:
        with get_db() as conn:
            conn.execute(
                "UPDATE job_state SET next_run_at = ? WHERE id = 1",
                (next_run_at,)
            )


# ── Job state ──────────────────────────────────────────────────────────────────

def get_job_state() -> dict:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM job_state WHERE id = 1").fetchone()
    return dict(row) if row else {}


def set_job_running(job_id: str, is_scheduled: bool):
    with get_db() as conn:
        conn.execute("""
            UPDATE job_state
            SET status='running', is_scheduled=?, current_job_id=?,
                started_at=?, finished_at=NULL,
                courses_scraped=NULL, courses_skipped=NULL
            WHERE id = 1
        """, (1 if is_scheduled else 0, job_id,
              datetime.utcnow().isoformat()))


def set_job_finished(job_id: str, status: str,
                     courses_scraped: int, courses_skipped: int,
                     next_run_at: str = None):
    with get_db() as conn:
        conn.execute("""
            UPDATE job_state
            SET status=?, finished_at=?,
                courses_scraped=?, courses_skipped=?,
                next_run_at=COALESCE(?, next_run_at)
            WHERE id = 1
        """, (status, datetime.utcnow().isoformat(),
              courses_scraped, courses_skipped, next_run_at))
        conn.execute(
            "UPDATE settings SET last_job_id = ? WHERE id = 1", (job_id,)
        )


# ── Job history ────────────────────────────────────────────────────────────────

def append_job_history(record: dict):
    """Append one record to data/jobs.json (creates file if absent)."""
    os.makedirs(os.path.dirname(config.JOBS_JSON), exist_ok=True)
    history = []
    if os.path.exists(config.JOBS_JSON):
        try:
            with open(config.JOBS_JSON, "r", encoding="utf-8") as f:
                history = json.load(f)
        except (json.JSONDecodeError, OSError):
            history = []
    history.append(record)
    with open(config.JOBS_JSON, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


# ── Course count ───────────────────────────────────────────────────────────────

def count_courses() -> int:
    """Count non-blank lines in the 'included' column of course-list.csv."""
    import csv
    path = config.COURSE_CSV
    if not os.path.exists(path):
        return 0
    count = 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i == 0:
                    continue  # skip header
                if row and row[0].strip():
                    count += 1
    except OSError:
        return 0
    return count
