"""
app/auth.py — Authentication helpers for JacDash.

Supports two modes:
- sso   : REMOTE_USER provided by upstream auth (Shibboleth/proxy)
- local : username/password login persisted in Flask session
"""

import os
from functools import wraps
from flask import request, render_template, current_app, session, redirect, url_for
import config
import db


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


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        username = get_current_user()
        if not username:
            if config.AUTH_MODE == "local":
                return redirect(url_for("views.login"))
            return render_template("403.html", reason="No authenticated session detected."), 403

        if config.AUTH_MODE == "local":
            user = db.get_user_by_username(username)
            if not user or not user.get("is_active"):
                session.clear()
                return redirect(url_for("views.login"))
            return f(*args, **kwargs)

        if not db.user_exists(username):
            return render_template(
                "403.html",
                reason=f"Your UQ account ({username}) is not authorised to use JacDash. "
                       "Please ask an existing JacDash administrator to add you."
            ), 403
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
