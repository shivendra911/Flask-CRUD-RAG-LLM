import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.config import Config

# ── Extension instances (created once, initialised in create_app) ──────────
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
migrate = Migrate()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)


def create_app(config_class=Config):
    """Application factory — creates and configures the Flask app."""

    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure critical directories exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Initialise extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

    # Flask-Login configuration
    login_manager.login_view = "main.login"
    login_manager.login_message_category = "info"

    # ── User loader callback ──────────────────────────────────────────
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ── Register blueprints ─────────────────────────────────────────
    from app.routes import main
    from app.admin_routes import admin_bp

    app.register_blueprint(main)
    app.register_blueprint(admin_bp)

    # ── Error handlers ────────────────────────────────────────────────
    from flask import render_template, jsonify

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        return (
            jsonify(
                {
                    "error": "Too many requests. Please wait a moment before trying again.",
                    "retry_after": str(e.description),
                }
            ),
            429,
        )

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    # ── CLI commands ──────────────────────────────────────────────────
    import click

    @app.cli.command("create-admin")
    @click.argument("username")
    def create_admin(username):
        """Promote an existing user to admin role."""
        user = User.query.filter_by(username=username).first()
        if not user:
            click.echo(f"Error: User '{username}' not found.")
            return
        user.role = "admin"
        db.session.commit()
        click.echo(f"✓ User '{username}' is now an admin.")

    # Create tables on first run (development convenience)
    with app.app_context():
        db.create_all()

    return app
