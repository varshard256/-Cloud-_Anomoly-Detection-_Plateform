from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user

from app.models import CloudServer, CloudMetric
from app.services.metrics_simulator import generate_tick

monitoring_bp = Blueprint("monitoring", __name__, url_prefix="/monitoring",
                           template_folder="../templates/monitoring")


def _visible_servers():
    if current_user.is_admin:
        return CloudServer.query.all()
    return CloudServer.query.filter_by(owner_id=current_user.id).all()


@monitoring_bp.route("/")
@login_required
def index():
    servers = _visible_servers()
    return render_template("monitoring/index.html", servers=servers)


@monitoring_bp.route("/<int:server_id>")
@login_required
def server_detail(server_id):
    server = CloudServer.query.get_or_404(server_id)
    if not (current_user.is_admin or server.owner_id == current_user.id):
        return render_template("errors/403.html"), 403
    return render_template("monitoring/server.html", server=server)


@monitoring_bp.route("/api/tick", methods=["POST"])
@login_required
def api_tick():
    """Advance the simulation by one tick for all servers the user can see
    (or a single server, if server_id is given). This is what the dashboard's
    live-refresh JS polls every few seconds."""
    server_id = request.args.get("server_id", type=int)
    servers = _visible_servers()
    if server_id:
        servers = [s for s in servers if s.id == server_id]

    latest = []
    for server in servers:
        metric = generate_tick(server)
        latest.append({"server_id": server.id, "server_name": server.name, **metric.to_dict(),
                        "health": server.health})

    return jsonify({"status": "ok", "count": len(latest), "metrics": latest})


@monitoring_bp.route("/api/history")
@login_required
def api_history():
    server_id = request.args.get("server_id", type=int)
    limit = request.args.get("limit", 100, type=int)
    if not server_id:
        return jsonify({"status": "error", "message": "server_id is required"}), 400

    server = CloudServer.query.get_or_404(server_id)
    if not (current_user.is_admin or server.owner_id == current_user.id):
        return jsonify({"status": "error", "message": "Not authorized"}), 403

    rows = (
        CloudMetric.query.filter_by(server_id=server_id)
        .order_by(CloudMetric.timestamp.desc()).limit(limit).all()
    )
    return jsonify({"status": "ok", "data": [m.to_dict() for m in reversed(rows)]})
