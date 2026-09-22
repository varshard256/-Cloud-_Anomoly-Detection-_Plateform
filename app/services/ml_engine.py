"""
ML Training Engine
--------------------
Trains and compares four anomaly-detection algorithms on cloud telemetry:

  - Isolation Forest    (unsupervised)
  - One-Class SVM       (unsupervised)
  - Random Forest       (supervised)
  - Decision Tree       (supervised)

Ground truth comes from CloudMetric.is_anomalous, which the simulator (or an
uploaded labeled CSV) sets. Models are evaluated on a chronological hold-out
split, scored on accuracy/precision/recall/F1/ROC-AUC, and the highest-F1
model is automatically marked active for live detection.
"""

import json
import os
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from flask import current_app
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.svm import OneClassSVM
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix,
)

from app.extensions import db
from app.models import CloudMetric, MLModel, Dataset

FEATURE_COLUMNS = [
    "cpu_usage", "memory_usage", "disk_usage", "disk_io",
    "network_throughput", "network_latency", "packet_loss", "bandwidth",
    "response_time", "error_rate", "request_rate",
]

MODEL_SPECS = {
    "isolation_forest": {"label": "Isolation Forest", "kind": "unsupervised"},
    "one_class_svm": {"label": "One-Class SVM", "kind": "unsupervised"},
    "random_forest": {"label": "Random Forest", "kind": "supervised"},
    "decision_tree": {"label": "Decision Tree", "kind": "supervised"},
}


def _load_training_frame(dataset: Dataset | None) -> pd.DataFrame:
    """Load features+labels either from an uploaded CSV Dataset or from the
    live CloudMetric table across all servers."""
    if dataset is not None:
        df = pd.read_csv(dataset.file_path)
        missing = [c for c in FEATURE_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"Uploaded dataset is missing required columns: {missing}")
        if "is_anomalous" not in df.columns:
            df["is_anomalous"] = 0
        if "timestamp" not in df.columns:
            df["timestamp"] = pd.date_range(end=datetime.utcnow(), periods=len(df), freq="15min")
        else:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df

    rows = CloudMetric.query.order_by(CloudMetric.timestamp.asc()).all()
    if not rows:
        raise ValueError("No metrics available yet. Add a server and let it collect data, or upload a dataset.")
    data = [{**{c: getattr(r, c) for c in FEATURE_COLUMNS}, "is_anomalous": int(r.is_anomalous),
             "timestamp": r.timestamp} for r in rows]
    return pd.DataFrame(data)


def _chronological_split(df: pd.DataFrame, test_frac=0.2):
    df_sorted = df.sort_values("timestamp").reset_index(drop=True)
    split_idx = max(1, int(len(df_sorted) * (1 - test_frac)))
    return df_sorted.iloc[:split_idx], df_sorted.iloc[split_idx:]


def _safe_roc_auc(y_true, scores):
    try:
        if len(set(y_true)) < 2:
            return None
        return round(float(roc_auc_score(y_true, scores)), 3)
    except Exception:
        return None


def train_all_models(trained_by: int, dataset_id: int | None = None) -> list[MLModel]:
    """Train all 4 models, persist artifacts + DB rows, and auto-activate
    the best (highest F1) one. Returns the list of created MLModel rows."""
    dataset = Dataset.query.get(dataset_id) if dataset_id else None
    df = _load_training_frame(dataset)

    if df["is_anomalous"].nunique() < 2:
        # Can't compute supervised metrics meaningfully without both classes;
        # still proceed (Isolation Forest/OCSVM work fine unsupervised).
        pass

    train_df, test_df = _chronological_split(df)
    X_train_raw = train_df[FEATURE_COLUMNS].values
    y_train = train_df["is_anomalous"].astype(int).values
    X_test_raw = test_df[FEATURE_COLUMNS].values
    y_test = test_df["is_anomalous"].astype(int).values

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train_raw)
    X_test = scaler.transform(X_test_raw)

    contamination = float(np.clip(y_train.mean() if y_train.mean() > 0 else 0.05, 0.01, 0.4))
    model_dir = current_app.config["MODEL_FOLDER"]
    timestamp_tag = datetime.utcnow().strftime("%Y%m%d%H%M%S")

    results = []

    # ---- 1. Isolation Forest (unsupervised) --------------------------
    iso = IsolationForest(n_estimators=200, contamination=contamination, random_state=42, n_jobs=-1)
    iso.fit(X_train)
    raw = iso.decision_function(X_test)
    score = (raw.max() - raw) / (raw.max() - raw.min() + 1e-9)  # higher = more anomalous
    pred = (iso.predict(X_test) == -1).astype(int)
    results.append(("isolation_forest", iso, pred, score))

    # ---- 2. One-Class SVM (unsupervised) ------------------------------
    ocsvm = OneClassSVM(kernel="rbf", nu=contamination, gamma="scale")
    ocsvm.fit(X_train)
    raw2 = ocsvm.decision_function(X_test)
    score2 = (raw2.max() - raw2) / (raw2.max() - raw2.min() + 1e-9)
    pred2 = (ocsvm.predict(X_test) == -1).astype(int)
    results.append(("one_class_svm", ocsvm, pred2, score2))

    # ---- 3. Random Forest (supervised) --------------------------------
    rf = RandomForestClassifier(n_estimators=300, max_depth=10, class_weight="balanced",
                                 random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    pred3 = rf.predict(X_test)
    score3 = rf.predict_proba(X_test)[:, 1] if len(rf.classes_) > 1 else np.zeros(len(X_test))
    results.append(("random_forest", rf, pred3, score3))

    # ---- 4. Decision Tree (supervised) --------------------------------
    dt = DecisionTreeClassifier(max_depth=8, class_weight="balanced", random_state=42)
    dt.fit(X_train, y_train)
    pred4 = dt.predict(X_test)
    score4 = dt.predict_proba(X_test)[:, 1] if len(dt.classes_) > 1 else np.zeros(len(X_test))
    results.append(("decision_tree", dt, pred4, score4))

    created = []
    for model_key, fitted_model, pred, score in results:
        acc = round(float(accuracy_score(y_test, pred)), 3) if len(y_test) else 0.0
        prec = round(float(precision_score(y_test, pred, zero_division=0)), 3)
        rec = round(float(recall_score(y_test, pred, zero_division=0)), 3)
        f1 = round(float(f1_score(y_test, pred, zero_division=0)), 3)
        roc_auc = _safe_roc_auc(y_test, score)
        cm = confusion_matrix(y_test, pred, labels=[0, 1]).tolist() if len(y_test) else [[0, 0], [0, 0]]

        feature_importance = {}
        if hasattr(fitted_model, "feature_importances_"):
            feature_importance = {
                col: round(float(imp), 4)
                for col, imp in zip(FEATURE_COLUMNS, fitted_model.feature_importances_)
            }

        artifact_path = os.path.join(model_dir, f"{model_key}_{timestamp_tag}.joblib")
        scaler_path = os.path.join(model_dir, f"{model_key}_{timestamp_tag}_scaler.joblib")
        joblib.dump(fitted_model, artifact_path)
        joblib.dump(scaler, scaler_path)

        # Deactivate any previous model of this run's dataset scope before inserting
        row = MLModel(
            name=f"{MODEL_SPECS[model_key]['label']} ({timestamp_tag})",
            model_type=model_key,
            dataset_id=dataset.id if dataset else None,
            trained_by=trained_by,
            file_path=artifact_path,
            accuracy=acc,
            precision_score=prec,
            recall_score=rec,
            f1_score=f1,
            roc_auc=roc_auc,
            confusion_matrix_json=json.dumps(cm),
            feature_importance_json=json.dumps(feature_importance),
            is_active=False,
        )
        db.session.add(row)
        created.append(row)

    db.session.flush()  # assign IDs

    # Auto-select best by F1 (ties broken by ROC-AUC then recall)
    def sort_key(r):
        return (r.f1_score or 0, r.roc_auc or 0, r.recall_score or 0)

    best = max(created, key=sort_key)
    MLModel.query.filter(MLModel.is_active.is_(True)).update({"is_active": False})
    best.is_active = True

    if dataset:
        dataset.status = "trained"

    db.session.commit()
    return created


def scaler_path_for(model: MLModel) -> str:
    """Scaler artifacts are always saved alongside the model using a fixed
    naming convention (see train_all_models), so no extra DB column is needed."""
    return model.file_path.replace(".joblib", "_scaler.joblib")


def get_active_model():
    return MLModel.query.filter_by(is_active=True).order_by(MLModel.trained_at.desc()).first()


def activate_model(model_id: int):
    MLModel.query.filter(MLModel.is_active.is_(True)).update({"is_active": False})
    m = MLModel.query.get_or_404(model_id)
    m.is_active = True
    db.session.commit()
    return m
