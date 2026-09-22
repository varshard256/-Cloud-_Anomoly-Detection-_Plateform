import os

from flask import Flask, render_template

from app.extensions import db, login_manager, mail, csrf, migrate


def create_app(config_name=None):
    app = Flask(__name__)

    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    from config.config import config_by_name
    app.config.from_object(config_by_name[config_name])

    # Ensure runtime folders exist
    for folder in (app.config["UPLOAD_FOLDER"], app.config["DATASET_FOLDER"],
                   app.config["REPORT_FOLDER"], app.config["MODEL_FOLDER"],
                   app.config["LOG_FOLDER"]):
        os.makedirs(folder, exist_ok=True)

    # --- extensions ---------------------------------------------------
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    csrf.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to access that page."
    login_manager.login_message_category = "info"

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # --- blueprints ------------------------------------------------
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.admin import admin_bp
    from app.routes.servers import servers_bp
    from app.routes.monitoring import monitoring_bp
    from app.routes.ai import ai_bp
    from app.routes.alerts import alerts_bp
    from app.routes.reports import reports_bp
    from app.routes.analytics import analytics_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(servers_bp)
    app.register_blueprint(monitoring_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(analytics_bp)

    # --- error handlers ------------------------------------------------
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    # --- template globals -----------------------------------------------
    @app.context_processor
    def inject_globals():
        from datetime import datetime
        from flask_login import current_user
        unread = 0
        if current_user.is_authenticated:
            from app.models import Alert
            unread = Alert.query.filter_by(user_id=current_user.id, is_read=False).count()
        return {"current_year": datetime.utcnow().year, "app_name": "NeuroCloud", "unread_alert_count": unread}

    return app
