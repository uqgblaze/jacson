"""
app/views.py — Main page route for JacDash.
"""

import flask
from flask import Blueprint, render_template, redirect, url_for
from werkzeug.security import check_password_hash
from app.auth import require_auth, get_current_user
import config
import db

views_bp = Blueprint("views", __name__)


@views_bp.route("/")
@require_auth
def index():
    return render_template(
        "index.html",
        username=get_current_user(),
        google_sheet_url=config.GOOGLE_SHEET_URL,
        ultra_builder_url=config.ULTRA_BUILDER_URL,
        github_url=config.GITHUB_URL,
    )


@views_bp.route("/login", methods=["GET", "POST"])
def login():
    if config.AUTH_MODE != "local":
        return redirect(url_for("views.index"))

    error = ""
    if flask.request.method == "POST":
        username = (flask.request.form.get("username") or "").strip().lower()
        password = flask.request.form.get("password") or ""
        user = db.get_user_by_username(username)
        if user and user.get("is_active") and user.get("password_hash") and check_password_hash(user["password_hash"], password):
            flask.session.clear()
            flask.session["username"] = username
            flask.session["is_admin"] = bool(user.get("is_admin"))
            db.set_last_login(username)
            return redirect(url_for("views.index"))
        error = "Invalid username or password."

    return render_template("login.html", error=error)


@views_bp.route("/logout", methods=["POST"])
def logout():
    flask.session.clear()
    return redirect(url_for("views.login"))
