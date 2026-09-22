from datetime import datetime

from app.extensions import db


class CloudMetric(db.Model):
    __tablename__ = "cloud_metrics"

    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey("cloud_servers.id"), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    cpu_usage = db.Column(db.Float, default=0)          # %
    memory_usage = db.Column(db.Float, default=0)        # %
    disk_usage = db.Column(db.Float, default=0)          # %
    disk_io = db.Column(db.Float, default=0)             # MB/s
    network_throughput = db.Column(db.Float, default=0)  # Mbps
    network_latency = db.Column(db.Float, default=0)     # ms
    packet_loss = db.Column(db.Float, default=0)         # %
    bandwidth = db.Column(db.Float, default=0)           # Mbps
    response_time = db.Column(db.Float, default=0)       # ms
    availability = db.Column(db.Float, default=100)      # %
    error_rate = db.Column(db.Float, default=0)          # %
    request_rate = db.Column(db.Float, default=0)        # req/s
    storage_usage = db.Column(db.Float, default=0)       # GB
    process_count = db.Column(db.Integer, default=0)
    active_connections = db.Column(db.Integer, default=0)
    temperature = db.Column(db.Float, default=0)         # C (simulated)
    power_consumption = db.Column(db.Float, default=0)   # Watts (simulated)

    is_anomalous = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "disk_usage": self.disk_usage,
            "disk_io": self.disk_io,
            "network_throughput": self.network_throughput,
            "network_latency": self.network_latency,
            "packet_loss": self.packet_loss,
            "bandwidth": self.bandwidth,
            "response_time": self.response_time,
            "availability": self.availability,
            "error_rate": self.error_rate,
            "request_rate": self.request_rate,
            "storage_usage": self.storage_usage,
            "process_count": self.process_count,
            "active_connections": self.active_connections,
            "temperature": self.temperature,
            "power_consumption": self.power_consumption,
            "is_anomalous": self.is_anomalous,
        }
