"""
Recommendation Engine
------------------------
Rule-based mapping from a detected anomaly's metric profile to a likely
root cause and a concrete remediation action. Sits downstream of the ML
detection engine — it doesn't decide *whether* something is anomalous
(that's the model's job), only *what to do about it*.
"""

from app.models import Recommendation

RULES = [
    # (condition(metric), action_type, text, priority)
    (lambda m: m.cpu_usage >= 90, "scale_vm",
     "CPU usage is critically high. Scale out to an additional instance or upgrade to a higher CPU tier; "
     "check for runaway processes or inefficient queries.", "critical"),
    (lambda m: m.cpu_usage >= 75, "investigate_high_cpu",
     "CPU usage is elevated. Investigate top processes and recent deployments before it reaches critical.", "medium"),
    (lambda m: m.memory_usage >= 90, "increase_ram",
     "Memory usage is critically high, likely a leak. Restart the affected service and increase allocated RAM.", "critical"),
    (lambda m: m.memory_usage >= 78, "investigate_high_cpu",
     "Memory usage is trending high. Profile the service for a possible leak before it impacts availability.", "medium"),
    (lambda m: m.disk_usage >= 90, "increase_storage",
     "Disk usage is critically high. Clean up old logs/temp files and provision additional storage.", "critical"),
    (lambda m: m.disk_usage >= 78, "clean_disk",
     "Disk usage is elevated. Schedule a cleanup job and review log rotation policy.", "medium"),
    (lambda m: m.network_throughput >= 150 or m.packet_loss >= 5, "investigate_security_threat",
     "Unusual network traffic volume or packet loss detected — possible DDoS or misconfigured retry loop. "
     "Enable rate limiting and inspect traffic source IPs.", "high"),
    (lambda m: m.response_time >= 400, "optimize_database",
     "Response time is significantly elevated. Check slow queries, connection pool saturation, and cache hit rate.", "high"),
    (lambda m: m.error_rate >= 8, "restart_service",
     "Error rate is elevated. Restart the affected service and check recent deployment/config changes.", "critical"),
    (lambda m: m.cpu_usage <= 3 and m.network_throughput <= 3, "investigate_high_cpu",
     "The instance appears idle or unresponsive. Verify health checks and recent deployment status.", "high"),
]


def generate_recommendations(anomaly, metric) -> list[Recommendation]:
    """Return (and persist) Recommendation rows for a given Anomaly + its
    source CloudMetric row. Always creates at least one generic recommendation
    if no specific rule matches."""
    created = []
    for condition, action_type, text, priority in RULES:
        try:
            if condition(metric):
                rec = Recommendation(
                    anomaly_id=anomaly.id,
                    action_type=action_type,
                    recommendation_text=text,
                    priority=priority,
                )
                created.append(rec)
        except Exception:
            continue

    if not created:
        created.append(Recommendation(
            anomaly_id=anomaly.id,
            action_type="investigate_high_cpu",
            recommendation_text="An unusual combined metric pattern was flagged. Manually inspect logs and "
                                 "recent configuration changes for this instance.",
            priority="medium",
        ))

    return created[:3]  # keep it focused — top 3 most relevant
