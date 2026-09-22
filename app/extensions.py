"""
Extension instances, created here (unbound) and initialized in the app
factory (app/__init__.py). Importing from this module instead of creating
new instances elsewhere avoids circular-import problems across blueprints.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_wtf import CSRFProtect
from flask_migrate import Migrate
from apscheduler.schedulers.background import BackgroundScheduler

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
csrf = CSRFProtect()
migrate = Migrate()
scheduler = BackgroundScheduler(daemon=True)
