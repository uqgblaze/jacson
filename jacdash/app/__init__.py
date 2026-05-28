"""
app/__init__.py — Flask application factory for JacDash.
"""

from flask import Flask
import config
import db


def create_app():
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.secret_key = config.SECRET_KEY
    app.config.from_object(config)

    # Initialise DB (creates tables + bootstrap user if needed)
    db.init_db()

    # Register blueprints
    from app.views import views_bp
    from app.api import api_bp
    from app.local_auth import local_auth_bp
    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(local_auth_bp)

    return app
