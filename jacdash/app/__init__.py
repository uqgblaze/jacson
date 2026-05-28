"""
app/__init__.py — Flask application factory for JacDash.
"""

from flask import Flask
from datetime import timedelta
import config
import db


def create_app():
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.secret_key = config.SECRET_KEY
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
    )

    # Initialise DB (creates tables + bootstrap user if needed)
    db.init_db()

    # Register blueprints
    from app.views import views_bp
    from app.api import api_bp
    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    return app
