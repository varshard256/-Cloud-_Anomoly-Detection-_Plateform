"""
Anomaly Detection Engine
---------------------------
Loads the currently active MLModel, scores CloudMetric rows that haven't
been evaluated yet, and — for anything flagged — creates an Anomaly row,
generates recommendations, and raises an Alert for the server's owner.
"""

import joblib
import numpy as np

from app.extensions import db
from app.models import CloudServer, CloudMetric, Anomaly, Alert
from app.services import ml_engine, recommendation_engine

SEVERITY_THRESHOLDS = [(80, "critical"), (60, "high"), (40, "medium"), (0, "low")]


def _severity_for(risk_score: float) -> str:
    for threshold, label in SEVERITY_THRESHOLDS:
        if risk_score >= threshold:
            return label
    return "low"


def _infer_anomaly_type(metric: CloudMetric) -> str:
    checks = [
        (metric.cpu_usage >= 85, "CPU Spike"),
        (metric.memory_usage >= 85, "Memory Leak"),
        (metric.disk_usage >= 85, "Disk Saturation"),
        (metric.network_throughput >= 130 or metric.packet_loss >= 5, "Network Congestion"),
        (metric.response_time >= 350, "High Response Time"),
        (metric.error_rate >= 7, "High Error Rate"),
    ]
    for condition, label in checks:
        if condition:
            return label
    return "Unexpected Traffic"


def run_detection(server_ids: list[int] | None = None, limit_per_server: int = 20) -> dict:
    """Score recent, not-yet-flagged metrics against the active model.
    Returns a summary dict for the UI."""
    active = ml_engine.get_active_model()
    if active is None:
        return {"status": "error", "message": "No active model. Train a model first."}

    model = joblib.load(active.file_path)
    scaler = joblib.load(ml_engine.scaler_path_for(active))

    query = CloudServer.query
    if server_ids:
        query = query.filter(CloudServer.id.in_(server_ids))
    servers = query.all()

    total_scored = 0
    anomalies_created = 0

    for server in servers:
        recent_metrics = (
            CloudMetric.query.filter_by(server_id=server.id)
            .order_by(CloudMetric.timestamp.desc())
            .limit(limit_per_server)
            .all()
        )
        if not recent_metrics:
            continue

        X = np.array([[getattr(m, c) for c in ml_engine.FEATURE_COLUMNS] for m in recent_metrics])
        X_scaled = scaler.transform(X)

        if active.model_type in ("isolation_forest", "one_class_svm"):
            raw = model.decision_function(X_scaled)
            scores = (raw.max() - raw) / (raw.max() - raw.min() + 1e-9)
            preds = (model.predict(X_scaled) == -1).astype(int)
        else:
            preds = model.predict(X_scaled)
            proba = model.predict_proba(X_scaled)
            scores = proba[:, 1] if proba.shape[1] > 1 else np.zeros(len(X_scaled))

        total_scored += len(recent_metrics)
        server_became_critical = False

        for metric, pred, score in zip(recent_metrics, preds, scores):
            already_flagged = Anomaly.query.filter_by(metric_id=metric.id).first()
            if already_flagged or not pred:
                continue

            risk_score = round(float(score) * 100, 2)
            severity = _severity_for(risk_score)
            anomaly = Anomaly(
                server_id=server.id,
                metric_id=metric.id,
                anomaly_type=_infer_anomaly_type(metric),
                severity=severity,
                anomaly_score=risk_score,
                description=f"Flagged by {active.name} (risk score {risk_score}/100).",
                model_used=active.model_type,
            )
            db.session.add(anomaly)
            db.session.flush()
            anomalies_created += 1

            for rec in recommendation_engine.generate_recommendations(anomaly, metric):
                db.session.add(rec)

            alert = Alert(
                user_id=server.owner_id,
                server_id=server.id,
                anomaly_id=anomaly.id,
                alert_type="anomaly",
                severity=severity,
                message=f"{anomaly.anomaly_type} detected on {server.name} (risk {risk_score}/100).",
            )
            db.session.add(alert)

            if severity == "critical":
                server_became_critical = True

        if server_became_critical:
            server.health = "critical"

    db.session.commit()
    return {
        "status": "ok",
        "servers_scanned": len(servers),
        "metrics_scored": total_scored,
        "anomalies_created": anomalies_created,
        "model_used": active.name,
    }
