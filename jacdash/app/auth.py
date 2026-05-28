"""
app/auth.py — Authentication helpers for JacDash.

UQ SSO (Shibboleth) terminates in Apache, which sets the REMOTE_USER
environment variable. Flask reads this via request.environ.
Every request is checked here: the user must exist in the users table.
"""

import os
from functools import wraps
from flask import request, render_template, current_app, session, redirect, url_for
import db


def get_remote_user() -> str | None:
    """
    Return the authenticated UQ username, or None if not set.

    In production, REMOTE_USER is injected into the WSGI environ by Apache/Shibboleth.
    In local dev (FLASK_DEBUG=1), falls back to the JACDASH_DEV_USER env var so you
    can test without SSO.
    """
    if current_app.config.get("LOCAL_AUTH_ENABLED"):
        user = session.get("local_auth_user")
        return user.strip().lower() if user else None

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
        if not username:
            if current_app.config.get("LOCAL_AUTH_ENABLED"):
                return redirect(url_for("local_auth.login_form"))
            return render_template("403.html", reason="No authenticated session detected."), 403
        if not db.user_exists(username):
            return render_template(
                "403.html",
                reason=f"Your UQ account ({username}) is not authorised to use JacDash. "
                        "Please ask an existing JacDash administrator to add you."
            ), 403
        return f(*args, **kwargs)
    return decorated
