from flask import current_app, render_template
from flask_mail import Message

from app.extensions import mail


def send_email(subject: str, recipients: list[str], template: str, **context) -> None:
    """Render an HTML email template and send it. Fails silently (logs only)
    if mail is not configured, so the rest of the app keeps working during
    local development without SMTP credentials."""
    try:
        msg = Message(subject=subject, recipients=recipients)
        msg.html = render_template(template, **context)
        mail.send(msg)
    except Exception as exc:  # pragma: no cover - best effort in dev
        current_app.logger.warning(f"Email send failed: {exc}")


def send_password_reset_email(user, reset_url: str) -> None:
    send_email(
        subject="Reset your NeuroCloud password",
        recipients=[user.email],
        template="emails/reset_password.html",
        user=user,
        reset_url=reset_url,
    )


def send_verification_email(user, verify_url: str) -> None:
    send_email(
        subject="Verify your NeuroCloud account",
        recipients=[user.email],
        template="emails/verify_email.html",
        user=user,
        verify_url=verify_url,
    )


def send_alert_email(user, alert) -> None:
    send_email(
        subject=f"[{alert.severity.upper()}] NeuroCloud Alert",
        recipients=[user.email],
        template="emails/alert_notification.html",
        user=user,
        alert=alert,
    )
