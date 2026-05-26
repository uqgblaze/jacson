"""
app/views.py — Main page route for JacDash.
"""

from flask import Blueprint, render_template
from app.auth import require_auth, get_remote_user
import config

views_bp = Blueprint("views", __name__)


@views_bp.route("/")
@require_auth
def index():
    return render_template(
        "index.html",
        username=get_remote_user(),
        google_sheet_url=config.GOOGLE_SHEET_URL,
        ultra_builder_url=config.ULTRA_BUILDER_URL,
        github_url=config.GITHUB_URL,
    )
