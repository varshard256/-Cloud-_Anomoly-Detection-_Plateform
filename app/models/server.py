from datetime import datetime

from app.extensions import db

SERVER_TYPES = ["Web Server", "Database Server", "App Server", "Cache Server",
                 "Load Balancer", "Kubernetes Node", "Storage Node"]
OS_CHOICES = ["Ubuntu 22.04", "Ubuntu 20.04", "CentOS 8", "Windows Server 2022",
              "Amazon Linux 2", "Debian 12"]
STATUS_CHOICES = ["running", "stopped", "maintenance"]
HEALTH_CHOICES = ["healthy", "warning", "critical"]


class CloudServer(db.Model):
    __tablename__ = "cloud_servers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)
    server_type = db.Column(db.String(50), default="Web Server")
    operating_system = db.Column(db.String(50), default="Ubuntu 22.04")
    location = db.Column(db.String(80), default="ap-south-1 (Mumbai)")

    cpu_cores = db.Column(db.Integer, default=4)
    memory_gb = db.Column(db.Integer, default=16)
    disk_gb = db.Column(db.Integer, default=100)

    status = db.Column(db.String(20), default="running")
    health = db.Column(db.String(20), default="healthy")
    uptime_seconds = db.Column(db.BigInteger, default=0)

    # per-server alert thresholds (overrides global config defaults)
    cpu_warning_threshold = db.Column(db.Float, default=75)
    cpu_critical_threshold = db.Column(db.Float, default=90)
    memory_warning_threshold = db.Column(db.Float, default=80)
    memory_critical_threshold = db.Column(db.Float, default=92)
    disk_warning_threshold = db.Column(db.Float, default=80)
    disk_critical_threshold = db.Column(db.Float, default=95)

    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    metrics = db.relationship("CloudMetric", backref="server", lazy="dynamic",
                               cascade="all, delete-orphan")
    anomalies = db.relationship("Anomaly", backref="server", lazy="dynamic",
                                 cascade="all, delete-orphan")
    predictions = db.relationship("Prediction", backref="server", lazy="dynamic",
                                   cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CloudServer {self.name} ({self.status})>"
