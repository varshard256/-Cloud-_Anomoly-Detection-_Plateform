from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Alert

alerts_bp = Blueprint("alerts", __name__, url_prefix="/alerts", template_folder="../templates/alerts")


@alerts_bp.route("/")
@login_required
def index():
    severity = request.args.get("severity")
    q = Alert.query.filter_by(user_id=current_user.id)
    if severity:
        q = q.filter_by(severity=severity)
    rows = q.order_by(Alert.created_at.desc()).limit(200).all()
    return render_template("alerts/list.html", alerts=rows)


@alerts_bp.route("/<int:alert_id>/read", methods=["POST"])
@login_required
def mark_read(alert_id):
    alert = Alert.query.get_or_404(alert_id)
    if alert.user_id == current_user.id:
        alert.is_read = True
        db.session.commit()
    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify({"status": "ok"})
    return redirect(url_for("alerts.index"))


@alerts_bp.route("/api/unread-count")
@login_required
def unread_count():
    count = Alert.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({"status": "ok", "count": count})
