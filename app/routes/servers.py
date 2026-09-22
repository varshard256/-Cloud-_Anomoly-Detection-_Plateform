from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.extensions import db
from app.models import CloudServer, CloudMetric, Anomaly
from app.models.server import SERVER_TYPES, OS_CHOICES
from app.services.metrics_simulator import seed_history
from app.utils.audit import log_action

servers_bp = Blueprint("servers", __name__, url_prefix="/servers", template_folder="../templates/servers")


def _visible_servers():
    if current_user.is_admin:
        return CloudServer.query.order_by(CloudServer.created_at.desc()).all()
    return CloudServer.query.filter_by(owner_id=current_user.id).order_by(CloudServer.created_at.desc()).all()


def _can_manage(server: CloudServer) -> bool:
    return current_user.is_admin or server.owner_id == current_user.id


@servers_bp.route("/")
@login_required
def list_servers():
    servers = _visible_servers()
    return render_template("servers/list.html", servers=servers, server_types=SERVER_TYPES)


@servers_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_server():
    if request.method == "POST":
        server = CloudServer(
            name=request.form.get("name", "").strip() or "Unnamed Server",
            ip_address=request.form.get("ip_address", "").strip() or "0.0.0.0",
            server_type=request.form.get("server_type", "Web Server"),
            operating_system=request.form.get("operating_system", "Ubuntu 22.04"),
            location=request.form.get("location", "ap-south-1 (Mumbai)").strip(),
            cpu_cores=int(request.form.get("cpu_cores") or 4),
            memory_gb=int(request.form.get("memory_gb") or 16),
            disk_gb=int(request.form.get("disk_gb") or 100),
            status=request.form.get("status", "running"),
            owner_id=current_user.id,
        )
        db.session.add(server)
        db.session.commit()

        seed_history(server, hours=24, interval_minutes=15)
        log_action("server_created", f"{server.name} ({server.server_type})", user_id=current_user.id)
        flash(f"{server.name} added and 24h of history seeded.", "success")
        return redirect(url_for("servers.detail", server_id=server.id))

    return render_template("servers/form.html", server=None, server_types=SERVER_TYPES, os_choices=OS_CHOICES)


@servers_bp.route("/<int:server_id>")
@login_required
def detail(server_id):
    server = CloudServer.query.get_or_404(server_id)
    if not _can_manage(server):
        flash("You don't have access to that server.", "danger")
        return redirect(url_for("servers.list_servers"))

    recent_metrics = (
        CloudMetric.query.filter_by(server_id=server.id)
        .order_by(CloudMetric.timestamp.desc()).limit(100).all()
    )
    recent_anomalies = (
        Anomaly.query.filter_by(server_id=server.id)
        .order_by(Anomaly.detected_at.desc()).limit(10).all()
    )
    return render_template("servers/detail.html", server=server,
                            recent_metrics=list(reversed(recent_metrics)),
                            recent_anomalies=recent_anomalies)


@servers_bp.route("/<int:server_id>/edit", methods=["GET", "POST"])
@login_required
def edit_server(server_id):
    server = CloudServer.query.get_or_404(server_id)
    if not _can_manage(server):
        flash("You don't have access to that server.", "danger")
        return redirect(url_for("servers.list_servers"))

    if request.method == "POST":
        server.name = request.form.get("name", server.name).strip()
        server.ip_address = request.form.get("ip_address", server.ip_address).strip()
        server.server_type = request.form.get("server_type", server.server_type)
        server.operating_system = request.form.get("operating_system", server.operating_system)
        server.location = request.form.get("location", server.location).strip()
        server.cpu_cores = int(request.form.get("cpu_cores") or server.cpu_cores)
        server.memory_gb = int(request.form.get("memory_gb") or server.memory_gb)
        server.disk_gb = int(request.form.get("disk_gb") or server.disk_gb)
        server.status = request.form.get("status", server.status)
        server.cpu_warning_threshold = float(request.form.get("cpu_warning_threshold") or server.cpu_warning_threshold)
        server.cpu_critical_threshold = float(request.form.get("cpu_critical_threshold") or server.cpu_critical_threshold)
        server.memory_warning_threshold = float(request.form.get("memory_warning_threshold") or server.memory_warning_threshold)
        server.memory_critical_threshold = float(request.form.get("memory_critical_threshold") or server.memory_critical_threshold)
        server.disk_warning_threshold = float(request.form.get("disk_warning_threshold") or server.disk_warning_threshold)
        server.disk_critical_threshold = float(request.form.get("disk_critical_threshold") or server.disk_critical_threshold)
        db.session.commit()
        log_action("server_updated", server.name, user_id=current_user.id)
        flash(f"{server.name} updated.", "success")
        return redirect(url_for("servers.detail", server_id=server.id))

    return render_template("servers/form.html", server=server, server_types=SERVER_TYPES, os_choices=OS_CHOICES)


@servers_bp.route("/<int:server_id>/delete", methods=["POST"])
@login_required
def delete_server(server_id):
    server = CloudServer.query.get_or_404(server_id)
    if not _can_manage(server):
        flash("You don't have access to that server.", "danger")
        return redirect(url_for("servers.list_servers"))

    name = server.name
    db.session.delete(server)
    db.session.commit()
    log_action("server_deleted", name, user_id=current_user.id)
    flash(f"{name} and its history were deleted.", "success")
    return redirect(url_for("servers.list_servers"))
