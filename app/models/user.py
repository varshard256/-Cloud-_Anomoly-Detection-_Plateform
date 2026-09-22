import secrets
from datetime import datetime, timedelta

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(20), nullable=False, default="user")  # 'admin' | 'user'
    is_active_account = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)

    avatar_url = db.Column(db.String(255), default="/static/img/default-avatar.png")

    reset_token = db.Column(db.String(100), unique=True, nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)

    verification_token = db.Column(db.String(100), unique=True, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    servers = db.relationship("CloudServer", backref="owner", lazy="dynamic",
                               foreign_keys="CloudServer.owner_id")
    alerts = db.relationship("Alert", backref="user", lazy="dynamic")

    # --- password helpers -------------------------------------------------
    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    # --- password reset -----------------------------------------------
    def generate_reset_token(self) -> str:
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
        return self.reset_token

    def verify_reset_token(self, token: str) -> bool:
        return (
            self.reset_token == token
            and self.reset_token_expiry is not None
            and self.reset_token_expiry > datetime.utcnow()
        )

    def clear_reset_token(self) -> None:
        self.reset_token = None
        self.reset_token_expiry = None

    # --- role helpers -------------------------------------------------
    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"
