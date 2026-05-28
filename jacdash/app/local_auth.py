"""Local username/password authentication routes."""

import secrets
from flask import Blueprint, current_app, render_template, request, session, redirect, url_for
from werkzeug.security import check_password_hash, generate_password_hash

import db

local_auth_bp = Blueprint("local_auth", __name__)


@local_auth_bp.route("/login", methods=["GET"])
def login_form():
    if not current_app.config.get("LOCAL_AUTH_ENABLED"):
        return redirect(url_for("views.index"))

    token = secrets.token_urlsafe(32)
    session["csrf_token"] = token
    return render_template("login.html", csrf_token=token)


@local_auth_bp.route("/login", methods=["POST"])
def login_submit():
    if not current_app.config.get("LOCAL_AUTH_ENABLED"):
        return redirect(url_for("views.index"))

    form_token = request.form.get("csrf_token", "")
    session_token = session.get("csrf_token")
    if not session_token or not secrets.compare_digest(form_token, session_token):
        return render_template("403.html", reason="Invalid CSRF token."), 403

    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "")

    user = db.get_user_by_username(username)
    password_hash = (user or {}).get("password_hash")
    if not user or not password_hash or not check_password_hash(password_hash, password):
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
        return render_template("login.html", csrf_token=token, error="Invalid username or password."), 401

    session.clear()
    session["local_auth_user"] = username
    session["csrf_token"] = secrets.token_urlsafe(32)
    session.permanent = True
    return redirect(url_for("views.index"))


@local_auth_bp.route("/logout", methods=["POST"])
def logout_submit():
    form_token = request.form.get("csrf_token", "")
    session_token = session.get("csrf_token")
    if not session_token or not secrets.compare_digest(form_token, session_token):
        return render_template("403.html", reason="Invalid CSRF token."), 403

    session.clear()
    return redirect(url_for("local_auth.login_form"))


def ensure_password_hash(username: str, raw_password: str):
    """Helper to initialize local credentials when needed."""
    db.set_user_password(username, generate_password_hash(raw_password))
