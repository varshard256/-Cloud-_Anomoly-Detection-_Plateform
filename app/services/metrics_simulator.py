"""
Cloud Metrics Simulator
-------------------------
Generates realistic, diurnal-patterned telemetry for each CloudServer and
persists it as CloudMetric rows. Occasionally injects a labeled anomaly
(is_anomalous=True) so the ML pipeline has ground truth to train and score
against — the same technique used in the anomaly-detection research paper
this project is built around.
"""

import random
from datetime import datetime, timedelta

import numpy as np

from app.extensions import db
from app.models import CloudServer, CloudMetric

ANOMALY_KINDS = [
    "CPU Spike", "Memory Leak", "Disk Saturation", "Network Congestion",
    "High Response Time", "High Error Rate",
]


def _diurnal_factor(hour: float) -> float:
    return 0.5 + 0.5 * np.sin((hour - 6) / 24 * 2 * np.pi)


def _base_profile(server: CloudServer) -> dict:
    """Baseline load shape per server type, so a DB server and a cache node
    don't look identical."""
    profiles = {
        "Database Server": dict(cpu=55, mem=70, disk=55, net=35, resp=120),
        "Cache Server": dict(cpu=25, mem=80, disk=10, net=55, resp=15),
        "Web Server": dict(cpu=35, mem=45, disk=20, net=60, resp=90),
        "App Server": dict(cpu=45, mem=55, disk=25, net=45, resp=110),
        "Load Balancer": dict(cpu=30, mem=30, disk=8, net=80, resp=25),
        "Kubernetes Node": dict(cpu=50, mem=60, disk=30, net=50, resp=70),
        "Storage Node": dict(cpu=20, mem=35, disk=70, net=40, resp=60),
    }
    return profiles.get(server.server_type, profiles["Web Server"])


def generate_tick(server: CloudServer, at: datetime | None = None, anomaly_rate: float = 0.05,
                   force_anomaly: str | None = None) -> CloudMetric:
    """Generate and persist a single new metric row for this server."""
    at = at or datetime.utcnow()
    p = _base_profile(server)
    factor = _diurnal_factor(at.hour + at.minute / 60)

    cpu = p["cpu"] * (0.6 + 0.8 * factor) + random.gauss(0, 4)
    mem = p["mem"] * (0.8 + 0.3 * factor) + random.gauss(0, 3)
    disk = p["disk"] * (0.9 + 0.2 * factor) + random.gauss(0, 2)
    net = p["net"] * (0.5 + 1.0 * factor) + random.gauss(0, 5)
    resp = p["resp"] * (0.7 + 0.6 * factor) + random.gauss(0, 8)

    disk_io = max(0, net * 0.4 + random.gauss(0, 3))
    latency = max(1, resp * 0.3 + random.gauss(0, 3))
    packet_loss = max(0, random.gauss(0.3, 0.4))
    bandwidth = max(0, net * 1.8 + random.gauss(0, 6))
    error_rate = max(0, random.gauss(0.8, 0.6))
    request_rate = max(0, net * 2.2 + random.gauss(0, 10))
    storage_usage = server.disk_gb * (disk / 100)
    process_count = int(max(20, random.gauss(120, 15)))
    active_connections = int(max(0, request_rate * 0.6 + random.gauss(0, 8)))
    temperature = 38 + (cpu / 100) * 22 + random.gauss(0, 1.5)
    power = 80 + (cpu / 100) * 140 + random.gauss(0, 6)
    availability = 100.0

    is_anomalous = False
    kind = force_anomaly
    if kind or random.random() < anomaly_rate:
        kind = kind or random.choice(ANOMALY_KINDS)
        is_anomalous = True
        if kind == "CPU Spike":
            cpu += random.uniform(35, 55)
        elif kind == "Memory Leak":
            mem += random.uniform(28, 42)
        elif kind == "Disk Saturation":
            disk += random.uniform(30, 45)
            disk_io += random.uniform(40, 70)
        elif kind == "Network Congestion":
            net += random.uniform(70, 130)
            packet_loss += random.uniform(4, 9)
        elif kind == "High Response Time":
            resp += random.uniform(250, 500)
            latency += random.uniform(80, 160)
        elif kind == "High Error Rate":
            error_rate += random.uniform(8, 18)
            availability = max(80, availability - random.uniform(5, 15))

    metric = CloudMetric(
        server_id=server.id,
        timestamp=at,
        cpu_usage=round(float(np.clip(cpu, 0, 100)), 2),
        memory_usage=round(float(np.clip(mem, 0, 100)), 2),
        disk_usage=round(float(np.clip(disk, 0, 100)), 2),
        disk_io=round(float(disk_io), 2),
        network_throughput=round(float(max(net, 0)), 2),
        network_latency=round(float(latency), 2),
        packet_loss=round(float(np.clip(packet_loss, 0, 100)), 2),
        bandwidth=round(float(bandwidth), 2),
        response_time=round(float(max(resp, 1)), 2),
        availability=round(float(np.clip(availability, 0, 100)), 2),
        error_rate=round(float(np.clip(error_rate, 0, 100)), 2),
        request_rate=round(float(request_rate), 2),
        storage_usage=round(float(storage_usage), 2),
        process_count=process_count,
        active_connections=active_connections,
        temperature=round(float(temperature), 1),
        power_consumption=round(float(power), 1),
        is_anomalous=is_anomalous,
    )
    db.session.add(metric)

    # Update server health snapshot from this latest reading
    if metric.cpu_usage >= server.cpu_critical_threshold or metric.memory_usage >= server.memory_critical_threshold \
            or metric.disk_usage >= server.disk_critical_threshold:
        server.health = "critical"
    elif metric.cpu_usage >= server.cpu_warning_threshold or metric.memory_usage >= server.memory_warning_threshold \
            or metric.disk_usage >= server.disk_warning_threshold:
        server.health = "warning"
    else:
        server.health = "healthy"
    server.uptime_seconds = (server.uptime_seconds or 0) + 15

    db.session.commit()
    return metric


def seed_history(server: CloudServer, hours: int = 48, interval_minutes: int = 15, anomaly_rate: float = 0.04):
    """Backfill historical metrics for a newly added server, so charts and
    model training have something to work with immediately."""
    start = datetime.utcnow() - timedelta(hours=hours)
    n_points = int(hours * 60 / interval_minutes)
    for i in range(n_points):
        ts = start + timedelta(minutes=i * interval_minutes)
        generate_tick(server, at=ts, anomaly_rate=anomaly_rate)
