from pathlib import Path
from flask import Flask, render_template
from config import Config
from app.extensions import db, migrate, login_manager, csrf

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "frontend"


def create_app(config_class=Config):
    flask_app = Flask(
        __name__,
        template_folder=str(FRONTEND_DIR / "templates"),
        static_folder=str(FRONTEND_DIR / "static"),
        static_url_path="/static",
    )
    if isinstance(config_class, dict):
        flask_app.config.from_object(Config)
        flask_app.config.update(config_class)
    else:
        flask_app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(flask_app)
    migrate.init_app(flask_app, db)
    login_manager.init_app(flask_app)
    csrf.init_app(flask_app)

    # Configure login manager
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Silakan masuk terlebih dahulu untuk mengakses halaman ini."
    login_manager.login_message_category = "warning"

    # Import models for Flask-Migrate & SQLAlchemy discovery
    from app import models  # noqa: F401
    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (ValueError, TypeError):
            return None

    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.citizen import citizen_bp
    from app.routes.admin import admin_bp
    from app.routes.facilities import facilities_bp
    from app.routes.assistant import assistant_bp

    flask_app.register_blueprint(main_bp)
    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(citizen_bp)
    flask_app.register_blueprint(admin_bp)
    flask_app.register_blueprint(facilities_bp)
    flask_app.register_blueprint(assistant_bp)

    # Register CLI commands
    from app.cli import register_cli_commands
    register_cli_commands(flask_app)

    # Template filters
    @flask_app.template_filter("rupiah")
    def format_rupiah(value):
        if value is None:
            return "Rp0"
        try:
            from decimal import Decimal
            val_int = int(round(Decimal(str(value))))
            formatted = f"{val_int:,}".replace(",", ".")
            return f"Rp{formatted}"
        except Exception:
            return f"Rp{value}"

    # Error handlers
    @flask_app.errorhandler(400)
    def bad_request_error(error):
        return render_template("errors/400.html"), 400

    @flask_app.errorhandler(403)
    def forbidden_error(error):
        return render_template("errors/403.html"), 403

    @flask_app.errorhandler(404)
    def not_found_error(error):
        return render_template("errors/404.html"), 404

    @flask_app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    return flask_app

