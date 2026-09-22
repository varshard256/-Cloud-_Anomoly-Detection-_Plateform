from collections import Counter
from datetime import datetime, timedelta

from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user

from app.models import CloudServer, CloudMetric, Anomaly

analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics", template_folder="../templates/analytics")


def _visible_server_ids():
    if current_user.is_admin:
        return [s.id for s in CloudServer.query.all()]
    return [s.id for s in CloudServer.query.filter_by(owner_id=current_user.id).all()]


@analytics_bp.route("/")
@login_required
def index():
    return render_template("analytics/index.html")


@analytics_bp.route("/api/summary")
@login_required
def api_summary():
    ids = _visible_server_ids()
    since = datetime.utcnow() - timedelta(days=7)

    anomalies = Anomaly.query.filter(Anomaly.server_id.in_(ids), Anomaly.detected_at >= since).all() if ids else []
    severity_counts = Counter(a.severity for a in anomalies)
    type_counts = Counter(a.anomaly_type for a in anomalies)

    server_counts = Counter(a.server_id for a in anomalies)
    servers_by_id = {s.id: s.name for s in CloudServer.query.filter(CloudServer.id.in_(ids)).all()} if ids else {}
    top_servers = [
        {"server": servers_by_id.get(sid, f"#{sid}"), "count": count}
        for sid, count in server_counts.most_common(5)
    ]

    # Fleet-wide average metrics over the last 100 readings per visible server
    cpu_vals, mem_vals, disk_vals, net_vals, err_vals = [], [], [], [], []
    for sid in ids:
        rows = (
            CloudMetric.query.filter_by(server_id=sid)
            .order_by(CloudMetric.timestamp.desc()).limit(100).all()
        )
        cpu_vals += [r.cpu_usage for r in rows]
        mem_vals += [r.memory_usage for r in rows]
        disk_vals += [r.disk_usage for r in rows]
        net_vals += [r.network_throughput for r in rows]
        err_vals += [r.error_rate for r in rows]

    def avg(vals):
        return round(sum(vals) / len(vals), 2) if vals else 0

    return jsonify({
        "status": "ok",
        "severity_counts": dict(severity_counts),
        "type_counts": dict(type_counts),
        "top_servers": top_servers,
        "fleet_averages": {
            "cpu_usage": avg(cpu_vals), "memory_usage": avg(mem_vals),
            "disk_usage": avg(disk_vals), "network_throughput": avg(net_vals),
            "error_rate": avg(err_vals),
        },
        "total_anomalies_7d": len(anomalies),
    })
