from flask import request

from app.extensions import db
from app.models import SystemLog


def log_action(action: str, description: str = "", level: str = "info", user_id: int | None = None) -> None:
    """Write an audit-trail row. Never raises — logging failures must not
    break the calling request."""
    try:
        entry = SystemLog(
            user_id=user_id,
            action=action,
            description=description,
            level=level,
            ip_address=request.remote_addr if request else None,
        )
        db.session.add(entry)
        db.session.commit()
    except Exception:
        db.session.rollback()
