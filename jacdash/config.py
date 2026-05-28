"""
config.py — JacDash configuration
Edit these values before deploying to UQCloud.
"""

import os
from datetime import timedelta

# ── Paths ──────────────────────────────────────────────────────────────────────
# Root of the JacDash application (this file's directory)
JACDASH_ROOT = os.path.dirname(os.path.abspath(__file__))

# Root of the JacSON project (one level up from jacdash/)
JACSON_ROOT = os.path.abspath(os.path.join(JACDASH_ROOT, ".."))

# Path to JacSON runner entrypoint (invokes scripts/scraper_runner.py)
RUN_JACSON = os.path.join(JACSON_ROOT, "run_JacSON.py")

# Path to course-list.csv used to count courses
COURSE_CSV = os.path.join(JACSON_ROOT, "course-list.csv")

# SQLite database file
DB_PATH = os.path.join(JACDASH_ROOT, "data", "jacdash.db")

# Job history JSON file
JOBS_JSON = os.path.join(JACDASH_ROOT, "data", "jobs.json")

# Log files directory (JacSON writes here; JacDash tails from here)
LOGS_DIR = os.path.join(JACSON_ROOT, "logs")

# ── Links ──────────────────────────────────────────────────────────────────────
# Edit Course List — Google Sheets URL
# Replace with your actual sheet URL if different.
GOOGLE_SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1tJ04EY1AtyS-7iKlmgZhmom0f97xK3DsZ88wkqmRwNs/edit?usp=sharing"
)

# Open Ultra Builder link (fixed)
ULTRA_BUILDER_URL = "https://uq-business-school.github.io/ibis/"

# GitHub repository link — shown in sidebar footer
# Replace with the canonical repo URL if it moves.
GITHUB_URL = "https://github.com/uq-course-profiles/jacson"

# ── Bootstrap user ────────────────────────────────────────────────────────────
# This user is inserted into the DB on first run so that someone can log in
# before any users have been added via the UI.
# Set to None to disable automatic seeding.
BOOTSTRAP_USER = ("uqgblaze", "Geoffrey Blazer")

# ── Flask ──────────────────────────────────────────────────────────────────────
# Change this to a long random string in production.
SECRET_KEY = os.environ.get("JACDASH_SECRET_KEY", "your-long-secret-key-here")
LOCAL_AUTH_ENABLED = os.environ.get("JACDASH_LOCAL_AUTH", "0") == "1"

# Session hardening
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = os.environ.get("JACDASH_SESSION_COOKIE_SECURE", "0") == "1"
PERMANENT_SESSION_LIFETIME = timedelta(
    minutes=int(os.environ.get("JACDASH_SESSION_IDLE_TIMEOUT_MINUTES", "60"))
)

# Local/LAN host + port (Raspberry Pi friendly default)
HOST = os.environ.get("JACDASH_HOST", "0.0.0.0")
PORT = int(os.environ.get("JACDASH_PORT", "1909"))

# ── Schedule defaults ─────────────────────────────────────────────────────────
# Applied when the settings row is first created.
DEFAULT_SCHEDULE_TIME = "03:00"
DEFAULT_SCHEDULE_DAYS = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"
