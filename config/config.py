"""
Application configuration.

DATABASE_URL is read from the environment. If it is not set, the app falls
back to a local SQLite file so the project runs out of the box with zero
external setup. For your final submission / deployment, set DATABASE_URL to
a MySQL connection string (see .env.example) to satisfy the MySQL
requirement.
"""

import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'database', 'neurocloud.db')}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    DATASET_FOLDER = os.path.join(BASE_DIR, "datasets")
    REPORT_FOLDER = os.path.join(BASE_DIR, "reports")
    MODEL_FOLDER = os.path.join(BASE_DIR, "app", "ml_models", "saved")
    LOG_FOLDER = os.path.join(BASE_DIR, "logs")
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25 MB upload limit

    ALLOWED_DATASET_EXTENSIONS = {"csv"}

    WTF_CSRF_ENABLED = True
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)

    # Mail
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "True") == "True"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", MAIL_USERNAME)
    MAIL_SUPPRESS_SEND = os.environ.get("MAIL_SUPPRESS_SEND", "False") == "True"

    # Real-time metric simulation
    METRIC_GENERATION_INTERVAL_SECONDS = 10

    # Alert thresholds (defaults; overridable per-server in Settings)
    CPU_WARNING_THRESHOLD = 75
    CPU_CRITICAL_THRESHOLD = 90
    MEMORY_WARNING_THRESHOLD = 80
    MEMORY_CRITICAL_THRESHOLD = 92
    DISK_WARNING_THRESHOLD = 80
    DISK_CRITICAL_THRESHOLD = 95


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_ECHO = False


class ProductionConfig(BaseConfig):
    DEBUG = False


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
