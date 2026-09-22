from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Report, CloudServer
from app.services import report_engine
from app.utils.audit import log_action

reports_bp = Blueprint("reports", __name__, url_prefix="/reports", template_folder="../templates/reports")


def _visible_server_ids():
    if current_user.is_admin:
        return None  # None = no filter, i.e. everything
    return [s.id for s in CloudServer.query.filter_by(owner_id=current_user.id).all()]


@reports_bp.route("/")
@login_required
def index():
    rows = Report.query.filter_by(generated_by=current_user.id).order_by(Report.created_at.desc()).all()
    return render_template("reports/list.html", reports=rows)


@reports_bp.route("/generate", methods=["POST"])
@login_required
def generate():
    report_type = request.form.get("report_type", "csv")
    generator = report_engine.GENERATORS.get(report_type)
    if not generator:
        flash("Unknown report type.", "danger")
        return redirect(url_for("reports.index"))

    path = generator(server_ids=_visible_server_ids())
    report = Report(
        title=f"Anomaly Report ({report_type.upper()})",
        report_type=report_type,
        file_path=path,
        generated_by=current_user.id,
    )
    db.session.add(report)
    db.session.commit()
    log_action("report_generated", report.title, user_id=current_user.id)
    flash(f"{report.title} generated.", "success")
    return redirect(url_for("reports.index"))


@reports_bp.route("/<int:report_id>/download")
@login_required
def download(report_id):
    report = Report.query.get_or_404(report_id)
    if report.generated_by != current_user.id and not current_user.is_admin:
        flash("Not authorized.", "danger")
        return redirect(url_for("reports.index"))
    return send_file(report.file_path, as_attachment=True)
