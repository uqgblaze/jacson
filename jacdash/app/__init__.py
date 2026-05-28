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

    # Initialise DB (creates tables + optional bootstrap admin)
    init_status = db.init_db()
    app.logger.info("[JacDash Bootstrap] %s", init_status["message"])

    # Register blueprints
    from app.views import views_bp
    from app.api import api_bp
    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    return app
