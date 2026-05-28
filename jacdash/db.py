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

from werkzeug.security import generate_password_hash

import config


def _normalize_username(username: str) -> str:
    return username.strip().lower()


def _ensure_user_auth_columns(conn: sqlite3.Connection):
    existing_columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "password_hash" not in existing_columns:
        conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
    if "is_admin" not in existing_columns:
        conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
    if "is_active" not in existing_columns:
        conn.execute("ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
    if "last_login_at" not in existing_columns:
        conn.execute("ALTER TABLE users ADD COLUMN last_login_at TEXT")


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
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                uq_username   TEXT    UNIQUE NOT NULL,
                full_name     TEXT    NOT NULL,
                password_hash TEXT,
                is_admin      INTEGER NOT NULL DEFAULT 0,
                is_active     INTEGER NOT NULL DEFAULT 1,
                last_login_at TEXT,
                created_at    TEXT    NOT NULL
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

        _ensure_user_auth_columns(conn)

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

        # Seed bootstrap user
        if config.BOOTSTRAP_USER:
            username, full_name = config.BOOTSTRAP_USER
            conn.execute("""
                INSERT OR IGNORE INTO users (uq_username, full_name, created_at)
                VALUES (?, ?, ?)
            """, (_normalize_username(username), full_name, datetime.utcnow().isoformat()))

            bootstrap_password = getattr(config, "BOOTSTRAP_ADMIN_PASSWORD", None) or os.environ.get("BOOTSTRAP_ADMIN_PASSWORD")
            if bootstrap_password:
                create_local_user(
                    username=username,
                    full_name=full_name,
                    password_hash=generate_password_hash(bootstrap_password),
                    is_admin=True,
                )

        if config.AUTH_MODE == "local":
            _ensure_local_admin(conn)


def _ensure_users_columns(conn):
    cols = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "password_hash" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
    if "is_admin" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
    if "is_active" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
    if "last_login_at" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN last_login_at TEXT")


def _ensure_local_admin(conn):
    row = conn.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1 AND is_active = 1").fetchone()
    if row and row[0] > 0:
        return
    username, full_name = config.BOOTSTRAP_USER or ("admin", "Local Administrator")
    username = username.strip().lower()
    password = os.environ.get("JACDASH_BOOTSTRAP_PASSWORD", "admin123")
    password_hash = generate_password_hash(password)
    conn.execute(
        """
        INSERT OR IGNORE INTO users (uq_username, full_name, created_at, password_hash, is_admin, is_active)
        VALUES (?, ?, ?, ?, 1, 1)
        """,
        (username, full_name, datetime.utcnow().isoformat(), password_hash),
    )
    conn.execute(
        """
        UPDATE users SET password_hash = COALESCE(password_hash, ?), is_admin = 1, is_active = 1
        WHERE uq_username = ?
        """,
        (password_hash, username),
    )

        if config.AUTH_MODE == "local":
            _ensure_local_admin(conn)


def _ensure_users_columns(conn):
    cols = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "password_hash" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
    if "is_admin" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
    if "is_active" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
    if "last_login_at" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN last_login_at TEXT")


def _ensure_local_admin(conn):
    row = conn.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1 AND is_active = 1").fetchone()
    if row and row[0] > 0:
        return
    username, full_name = config.BOOTSTRAP_USER or ("admin", "Local Administrator")
    username = username.strip().lower()
    password = os.environ.get("JACDASH_BOOTSTRAP_PASSWORD", "admin123")
    password_hash = generate_password_hash(password)
    conn.execute(
        """
        INSERT OR IGNORE INTO users (uq_username, full_name, created_at, password_hash, is_admin, is_active)
        VALUES (?, ?, ?, ?, 1, 1)
        """,
        (username, full_name, datetime.utcnow().isoformat(), password_hash),
    )
    conn.execute(
        """
        UPDATE users SET password_hash = COALESCE(password_hash, ?), is_admin = 1, is_active = 1
        WHERE uq_username = ?
        """,
        (password_hash, username),
    )


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
            "SELECT 1 FROM users WHERE uq_username = ?", (_normalize_username(uq_username),)
        ).fetchone()
    return row is not None


def get_user_by_username(uq_username: str):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE uq_username = ?", (uq_username.strip().lower(),)
        ).fetchone()
    return dict(row) if row else None


def set_last_login(uq_username: str):
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET last_login_at = ? WHERE uq_username = ?",
            (datetime.utcnow().isoformat(), uq_username.strip().lower()),
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
        conn.execute("DELETE FROM users WHERE uq_username = ?", (_normalize_username(uq_username),))


def get_user_by_username(username: str):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE uq_username = ?",
            (_normalize_username(username),),
        ).fetchone()
    return dict(row) if row else None


def create_local_user(username: str, full_name: str, password_hash: str, is_admin: bool = False):
    normalized_username = _normalize_username(username)
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO users (uq_username, full_name, password_hash, is_admin, is_active, created_at)
            VALUES (?, ?, ?, ?, 1, ?)
            ON CONFLICT(uq_username) DO UPDATE SET
                full_name=excluded.full_name,
                password_hash=excluded.password_hash,
                is_admin=excluded.is_admin,
                is_active=1
            """,
            (normalized_username, full_name.strip(), password_hash, 1 if is_admin else 0, now),
        )


def set_user_password(user_id: int, password_hash: str):
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (password_hash, user_id),
        )


def set_user_active(user_id: int, is_active: bool):
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET is_active = ? WHERE id = ?",
            (1 if is_active else 0, user_id),
        )


def list_users_with_roles():
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, uq_username, full_name, is_admin, is_active, last_login_at, created_at
            FROM users
            ORDER BY full_name
            """
        ).fetchall()
    return [dict(r) for r in rows]


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
