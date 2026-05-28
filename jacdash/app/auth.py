"""
app/auth.py — Authentication helpers for JacDash.

UQ SSO (Shibboleth) terminates in Apache, which sets the REMOTE_USER
environment variable. Flask reads this via request.environ.
Every request is checked here: the user must exist in the users table.
"""

import os
import re
from functools import wraps
from datetime import datetime, timedelta, timezone
from flask import request, render_template, current_app
import db
import config

_FAILED_ATTEMPTS = {}


def _client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def _throttle_key(username: str | None, ip: str) -> str:
    return f"{(username or 'unknown').lower()}|{ip}"


def _is_locked(key: str) -> bool:
    state = _FAILED_ATTEMPTS.get(key)
    if not state:
        return False
    locked_until = state.get("locked_until")
    return bool(locked_until and locked_until > datetime.now(timezone.utc))


def _record_failure(username: str | None, ip: str):
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=config.AUTH_LOCKOUT_WINDOW_SECONDS)
    key = _throttle_key(username, ip)
    state = _FAILED_ATTEMPTS.get(key, {"failures": []})
    failures = [ts for ts in state.get("failures", []) if ts >= window_start]
    failures.append(now)
    state["failures"] = failures
    if len(failures) >= config.AUTH_LOCKOUT_THRESHOLD:
        state["locked_until"] = now + timedelta(seconds=config.AUTH_LOCKOUT_SECONDS)
    _FAILED_ATTEMPTS[key] = state


def _clear_failures(username: str | None, ip: str):
    _FAILED_ATTEMPTS.pop(_throttle_key(username, ip), None)


def validate_password_policy(password: str) -> list[str]:
    errors = []
    if len(password) < config.PASSWORD_MIN_LENGTH:
        errors.append(f"Password must be at least {config.PASSWORD_MIN_LENGTH} characters.")
    if config.PASSWORD_REQUIRE_UPPER and not re.search(r"[A-Z]", password):
        errors.append("Password must include an uppercase letter.")
    if config.PASSWORD_REQUIRE_LOWER and not re.search(r"[a-z]", password):
        errors.append("Password must include a lowercase letter.")
    if config.PASSWORD_REQUIRE_DIGIT and not re.search(r"\d", password):
        errors.append("Password must include a digit.")
    if config.PASSWORD_REQUIRE_SPECIAL and not re.search(r"[^A-Za-z0-9]", password):
        errors.append("Password must include a special character.")
    return errors


def get_remote_user() -> str | None:
    """
    Return the authenticated UQ username, or None if not set.

    In production, REMOTE_USER is injected into the WSGI environ by Apache/Shibboleth.
    In local dev (FLASK_DEBUG=1), falls back to the JACDASH_DEV_USER env var so you
    can test without SSO.
    """
    user = request.environ.get("REMOTE_USER") or request.environ.get("HTTP_REMOTE_USER")
    if not user and current_app.debug:
        user = os.environ.get("JACDASH_DEV_USER")
    return user.strip() if user else None


def require_auth(f):
    """
    Decorator that enforces:
      1. REMOTE_USER is present (set by Apache/Shibboleth).
      2. REMOTE_USER exists in the users table.
    Returns 403 on failure.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        username = get_remote_user()
        ip = _client_ip()
        key = _throttle_key(username, ip)

        if _is_locked(key):
            db.log_auth_event("login", "locked", username=username, ip_address=ip, details="Temporary lockout in effect")
            return render_template("403.html", reason="Too many failed attempts. Please try again later."), 403

        if not username:
            _record_failure(username, ip)
            db.log_auth_event("login", "failed", ip_address=ip, details="No authenticated session detected")
            return render_template("403.html", reason="No authenticated session detected."), 403
        if not db.user_exists(username):
            _record_failure(username, ip)
            db.log_auth_event("login", "failed", username=username, ip_address=ip, details="User not authorised")
            return render_template(
                "403.html",
                reason=f"Your UQ account ({username}) is not authorised to use JacDash. "
                        "Please ask an existing JacDash administrator to add you."
            ), 403
        _clear_failures(username, ip)
        db.log_auth_event("login", "success", username=username, ip_address=ip)
        return f(*args, **kwargs)
    return decorated
