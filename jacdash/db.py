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
from datetime import datetime
from contextlib import contextmanager
from werkzeug.security import generate_password_hash

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


def init_db():
    """Create tables and seed bootstrap data if they don't exist yet."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                uq_username TEXT    UNIQUE NOT NULL,
                full_name   TEXT    NOT NULL,
                password_hash TEXT,
                created_at  TEXT    NOT NULL
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
        _ensure_user_password_hash_column(conn)

        conn.execute("""
            INSERT OR IGNORE INTO settings (id, schedule_time, schedule_days)
            VALUES (1, ?, ?)
        """, (config.DEFAULT_SCHEDULE_TIME, config.DEFAULT_SCHEDULE_DAYS))

        # Seed job_state row
        conn.execute("""
            INSERT OR IGNORE INTO job_state (id, status, is_scheduled)
            VALUES (1, 'idle', 0)
        """)

        # Seed bootstrap user
        if config.BOOTSTRAP_USER:
            username, full_name = config.BOOTSTRAP_USER
            conn.execute("""
                INSERT OR IGNORE INTO users (uq_username, full_name, created_at)
                VALUES (?, ?, ?)
            """, (username, full_name, datetime.utcnow().isoformat()))

        bootstrap_password = os.environ.get("JACDASH_BOOTSTRAP_PASSWORD")
        if bootstrap_password and config.BOOTSTRAP_USER:
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE uq_username = ?",
                (generate_password_hash(bootstrap_password), config.BOOTSTRAP_USER[0]),
            )


# ── Users ──────────────────────────────────────────────────────────────────────

def get_users():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT uq_username, full_name, created_at FROM users ORDER BY full_name"
        ).fetchall()
    return [dict(r) for r in rows]


def _ensure_user_password_hash_column(conn):
    cols = conn.execute("PRAGMA table_info(users)").fetchall()
    names = {c[1] for c in cols}
    if "password_hash" not in names:
        conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")


def user_exists(uq_username: str) -> bool:
    with get_db() as conn:
        row = conn.execute(
            "SELECT 1 FROM users WHERE uq_username = ?", (uq_username,)
        ).fetchone()
    return row is not None


def get_user_by_username(uq_username: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT uq_username, full_name, password_hash FROM users WHERE uq_username = ?",
            (uq_username.strip().lower(),),
        ).fetchone()
    return dict(row) if row else None


def set_user_password(uq_username: str, password_hash: str):
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE uq_username = ?",
            (password_hash, uq_username.strip().lower()),
        )


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
