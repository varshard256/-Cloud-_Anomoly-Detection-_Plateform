"""
Prediction Engine
--------------------
Lightweight forecasting for a server's future CPU/memory/disk usage and an
overall "failure probability" over the next N hours. Uses a RandomForest
regressor over lag + time-of-day features — deliberately simple (this is a
monitoring dashboard feature, not a research forecasting model), trained
fresh per request on that server's own history.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor

from app.extensions import db
from app.models import CloudMetric, Prediction

METRIC_MAP = {
    "cpu_usage": "cpu_usage",
    "memory_usage": "memory_usage",
    "disk_usage": "disk_usage",
}


def _build_features(df: pd.DataFrame, metric_col: str) -> pd.DataFrame:
    df = df.copy()
    df["hour"] = df["timestamp"].dt.hour
    df["lag1"] = df[metric_col].shift(1)
    df["lag2"] = df[metric_col].shift(2)
    df["rolling_mean"] = df[metric_col].rolling(3, min_periods=1).mean()
    return df.dropna()


def predict_server_metrics(server_id: int, horizon_hours: int = 24) -> dict:
    rows = (
        CloudMetric.query.filter_by(server_id=server_id)
        .order_by(CloudMetric.timestamp.asc())
        .all()
    )
    if len(rows) < 10:
        return {"status": "error", "message": "Not enough history yet — at least 10 data points are needed."}

    df = pd.DataFrame([{
        "timestamp": r.timestamp, "cpu_usage": r.cpu_usage,
        "memory_usage": r.memory_usage, "disk_usage": r.disk_usage,
        "is_anomalous": int(r.is_anomalous),
    } for r in rows])

    results = {}
    for metric_key in METRIC_MAP:
        feat_df = _build_features(df, metric_key)
        if len(feat_df) < 5:
            continue
        X = feat_df[["hour", "lag1", "lag2", "rolling_mean"]].values
        y = feat_df[metric_key].values

        model = RandomForestRegressor(n_estimators=150, max_depth=6, random_state=42)
        model.fit(X, y)

        # Walk the forecast forward hour by hour using the model's own predictions as new lags
        last_row = feat_df.iloc[-1]
        lag1, lag2 = last_row[metric_key], last_row["lag1"]
        rolling = last_row["rolling_mean"]
        preds = []
        now = datetime.utcnow()
        for h in range(1, horizon_hours + 1):
            hour_of_day = (now + timedelta(hours=h)).hour
            pred = float(model.predict([[hour_of_day, lag1, lag2, rolling]])[0])
            pred = float(np.clip(pred, 0, 100))
            preds.append({"hour_offset": h, "predicted_value": round(pred, 2)})
            lag2, lag1 = lag1, pred
            rolling = (rolling * 2 + pred) / 3

        results[metric_key] = preds

        # Persist a snapshot prediction (24h horizon point) for the dashboard history
        db.session.add(Prediction(
            server_id=server_id,
            metric_type=metric_key,
            horizon_hours=horizon_hours,
            predicted_value=preds[-1]["predicted_value"],
            failure_probability=0,
        ))

    # Failure probability blends two signals into a 0-100 score:
    #  1. How often this server has actually been flagged anomalous recently
    #     (weighted heavily — even a 5-10% anomaly rate is a real signal, not
    #     literally a 5-10% chance, so it's scaled up rather than used raw)
    #  2. How close current CPU/memory/disk are to "hot" territory, using a
    #     smooth ramp starting at 40% utilization rather than a hard cutoff,
    #     so the score moves well before something is already critical
    recent_anomaly_rate = df["is_anomalous"].tail(50).mean() if len(df) else 0
    anomaly_component = min(60, recent_anomaly_rate * 100 * 3)  # up to 60 pts

    latest = df.iloc[-1]
    resource_levels = [latest["cpu_usage"], latest["memory_usage"], latest["disk_usage"]]
    # Ramp: 0 pts at <=40% usage, scaling linearly up to 40 pts at 100% usage
    resource_component = np.mean([max(0, (level - 40) / 60 * 40) for level in resource_levels])

    failure_probability = round(float(np.clip(anomaly_component + resource_component, 0, 100)), 1)

    db.session.commit()

    return {
        "status": "ok",
        "server_id": server_id,
        "horizon_hours": horizon_hours,
        "forecast": results,
        "failure_probability": failure_probability,
    }
