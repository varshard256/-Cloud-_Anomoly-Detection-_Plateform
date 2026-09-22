"""
Creates (or promotes) an administrator account.

Usage:
    python create_admin.py
Reads ADMIN_EMAIL / ADMIN_PASSWORD from .env, or falls back to
admin@neurocloud.app / Admin@12345 if not set.
"""
import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.extensions import db
from app.models import User

app = create_app(os.environ.get("FLASK_ENV", "development"))

with app.app_context():
    db.create_all()

    email = os.environ.get("ADMIN_EMAIL", "admin@neurocloud.app")
    password = os.environ.get("ADMIN_PASSWORD", "Admin@12345")

    user = User.query.filter_by(email=email).first()
    if user:
        user.role = "admin"
        user.is_active_account = True
        user.email_verified = True
        print(f"Existing user {email} promoted to admin.")
    else:
        user = User(
            name="Administrator",
            email=email,
            role="admin",
            is_active_account=True,
            email_verified=True,
        )
        user.set_password(password)
        db.session.add(user)
        print(f"Admin account created: {email} / {password}")

    db.session.commit()
