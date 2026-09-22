from datetime import datetime

from app.extensions import db

SEVERITY_CHOICES = ["low", "medium", "high", "critical"]
ANOMALY_TYPES = [
    "CPU Spike", "Memory Leak", "Disk Saturation", "Network Congestion",
    "High Response Time", "High Error Rate", "Security Intrusion",
    "Abnormal Login", "Unexpected Traffic",
]


class Anomaly(db.Model):
    __tablename__ = "anomalies"

    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey("cloud_servers.id"), nullable=False, index=True)
    metric_id = db.Column(db.Integer, db.ForeignKey("cloud_metrics.id"), nullable=True)

    anomaly_type = db.Column(db.String(50), nullable=False)
    severity = db.Column(db.String(20), default="low")
    anomaly_score = db.Column(db.Float, default=0)  # model's raw decision score
    description = db.Column(db.Text)
    model_used = db.Column(db.String(50))  # isolation_forest / random_forest / etc.

    detected_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    resolved = db.Column(db.Boolean, default=False)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    alerts = db.relationship("Alert", backref="anomaly", lazy="dynamic")
    recommendations = db.relationship("Recommendation", backref="anomaly", lazy="dynamic",
                                       cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Anomaly {self.anomaly_type} [{self.severity}] server={self.server_id}>"


class Alert(db.Model):
    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    server_id = db.Column(db.Integer, db.ForeignKey("cloud_servers.id"), nullable=True)
    anomaly_id = db.Column(db.Integer, db.ForeignKey("anomalies.id"), nullable=True)

    alert_type = db.Column(db.String(50), default="anomaly")  # anomaly | system | security
    severity = db.Column(db.String(20), default="low")
    message = db.Column(db.String(255), nullable=False)

    is_read = db.Column(db.Boolean, default=False)
    email_sent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class Recommendation(db.Model):
    __tablename__ = "recommendations"

    id = db.Column(db.Integer, primary_key=True)
    anomaly_id = db.Column(db.Integer, db.ForeignKey("anomalies.id"), nullable=False)

    action_type = db.Column(db.String(50), nullable=False)  # restart_service | scale_vm | ...
    recommendation_text = db.Column(db.String(255), nullable=False)
    priority = db.Column(db.String(20), default="medium")

    applied = db.Column(db.Boolean, default=False)
    applied_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
