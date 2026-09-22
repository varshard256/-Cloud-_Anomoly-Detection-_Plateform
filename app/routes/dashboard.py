from flask import Blueprint, render_template
from flask_login import login_required, current_user

from app.models import CloudServer, Alert, Anomaly, CloudMetric

dashboard_bp = Blueprint("dashboard", __name__, template_folder="../templates/dashboard")


@dashboard_bp.route("/dashboard")
@login_required
def index():
    if current_user.is_admin:
        servers = CloudServer.query.all()
    else:
        servers = CloudServer.query.filter_by(owner_id=current_user.id).all()

    server_ids = [s.id for s in servers]
    open_alerts = (
        Alert.query.filter(Alert.user_id == current_user.id, Alert.is_read.is_(False))
        .order_by(Alert.created_at.desc())
        .limit(5)
        .all()
    )
    recent_anomalies = (
        Anomaly.query.filter(Anomaly.server_id.in_(server_ids))
        .order_by(Anomaly.detected_at.desc())
        .limit(5)
        .all()
        if server_ids else []
    )

    from datetime import datetime, timedelta
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    anomalies_today = (
        Anomaly.query.filter(Anomaly.server_id.in_(server_ids), Anomaly.detected_at >= today_start).count()
        if server_ids else 0
    )
    critical_alerts = (
        Anomaly.query.filter(Anomaly.server_id.in_(server_ids), Anomaly.severity == "critical").count()
        if server_ids else 0
    )

    cpu_vals, mem_vals, disk_vals, net_vals = [], [], [], []
    for sid in server_ids:
        rows = CloudMetric.query.filter_by(server_id=sid).order_by(CloudMetric.timestamp.desc()).limit(20).all()
        cpu_vals += [r.cpu_usage for r in rows]
        mem_vals += [r.memory_usage for r in rows]
        disk_vals += [r.disk_usage for r in rows]
        net_vals += [r.network_throughput for r in rows]

    def avg(vals):
        return round(sum(vals) / len(vals), 1) if vals else 0

    stats = {
        "total_servers": len(servers),
        "active_servers": len([s for s in servers if s.status == "running"]),
        "healthy_servers": len([s for s in servers if s.health == "healthy"]),
        "critical_servers": len([s for s in servers if s.health == "critical"]),
        "open_alerts": Alert.query.filter_by(user_id=current_user.id, is_read=False).count(),
        "anomalies_today": anomalies_today,
        "critical_alerts": critical_alerts,
        "cpu_avg": avg(cpu_vals),
        "memory_avg": avg(mem_vals),
        "disk_avg": avg(disk_vals),
        "network_avg": avg(net_vals),
    }

    return render_template(
        "dashboard/index.html",
        servers=servers,
        stats=stats,
        open_alerts=open_alerts,
        recent_anomalies=recent_anomalies,
    )
