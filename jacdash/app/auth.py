"""
app/auth.py — Authentication helpers for JacDash.

Supports two modes:
- sso   : REMOTE_USER provided by upstream auth (Shibboleth/proxy)
- local : username/password login persisted in Flask session
"""

import os
from functools import wraps
from flask import request, render_template, current_app, session
import db
import config


def get_remote_user() -> str | None:
    user = request.environ.get("REMOTE_USER") or request.environ.get("HTTP_REMOTE_USER")
    if not user and current_app.debug:
        user = os.environ.get("JACDASH_DEV_USER")
    return user.strip().lower() if user else None


def get_current_user() -> str | None:
    if config.AUTH_MODE == "local":
        user = session.get("username")
        return user.strip().lower() if user else None
    return get_remote_user()


def is_admin() -> bool:
    if config.AUTH_MODE != "local":
        return True
    return bool(session.get("is_admin"))


def get_current_user() -> str | None:
    """Return active username based on configured auth mode."""
    if config.AUTH_MODE == "sso":
        return get_remote_user()
    username = session.get("username")
    return username.strip() if isinstance(username, str) and username.strip() else None


def _local_session_valid() -> bool:
    """Validate required local-auth session keys and user access."""
    user_id = session.get("user_id")
    username = get_current_user()
    is_admin = session.get("is_admin")

    if not isinstance(user_id, int):
        return False
    if not username:
        return False
    if not isinstance(is_admin, bool):
        return False
    return db.user_exists(username)


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if config.AUTH_MODE == "sso":
            username = get_remote_user()
            if not username:
                return render_template("403.html", reason="No authenticated session detected."), 403
            if not db.user_exists(username):
                return render_template(
                    "403.html",
                    reason=f"Your UQ account ({username}) is not authorised to use JacDash. "
                            "Please ask an existing JacDash administrator to add you."
                ), 403
        else:
            if not _local_session_valid():
                return render_template("403.html", reason="No authenticated session detected."), 403
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    """Decorator enforcing admin-only access where configured."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if config.AUTH_MODE == "sso":
            # Backwards compatible: SSO deployment keeps existing behaviour.
            return f(*args, **kwargs)
        if not _local_session_valid() or not session.get("is_admin", False):
            return render_template("403.html", reason="Administrator access is required."), 403
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    @wraps(f)
    @require_auth
    def decorated(*args, **kwargs):
        if not is_admin():
            return render_template("403.html", reason="Administrator access is required."), 403
        return f(*args, **kwargs)
    return decorated
