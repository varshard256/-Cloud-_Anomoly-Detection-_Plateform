import os
import json
from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Dataset, MLModel, Anomaly, CloudServer, Recommendation
from app.services import ml_engine, anomaly_engine, prediction_engine
from app.utils.audit import log_action

ai_bp = Blueprint("ai", __name__, url_prefix="/ai", template_folder="../templates/ai")


def _visible_server_ids():
    if current_user.is_admin:
        return [s.id for s in CloudServer.query.all()]
    return [s.id for s in CloudServer.query.filter_by(owner_id=current_user.id).all()]


# ---------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------

@ai_bp.route("/datasets", methods=["GET", "POST"])
@login_required
def datasets():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename.lower().endswith(".csv"):
            flash("Please upload a .csv file.", "danger")
            return redirect(url_for("ai.datasets"))

        filename = secure_filename(f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}")
        path = os.path.join(current_app.config["DATASET_FOLDER"], filename)
        file.save(path)

        import pandas as pd
        try:
            df = pd.read_csv(path)
        except Exception as e:
            flash(f"Could not read CSV: {e}", "danger")
            return redirect(url_for("ai.datasets"))

        ds = Dataset(
            filename=filename, original_filename=file.filename, file_path=path,
            uploaded_by=current_user.id, row_count=len(df), column_count=len(df.columns),
            status="uploaded",
        )
        db.session.add(ds)
        db.session.commit()
        log_action("dataset_uploaded", ds.original_filename, user_id=current_user.id)
        flash(f"Dataset '{ds.original_filename}' uploaded ({ds.row_count} rows).", "success")
        return redirect(url_for("ai.datasets"))

    all_datasets = Dataset.query.order_by(Dataset.uploaded_at.desc()).all()
    return render_template("ai/datasets.html", datasets=all_datasets)


# ---------------------------------------------------------------------
# Training + model comparison
# ---------------------------------------------------------------------

@ai_bp.route("/train", methods=["GET", "POST"])
@login_required
def train():
    if request.method == "POST":
        dataset_id = request.form.get("dataset_id", type=int) or None
        try:
            created = ml_engine.train_all_models(trained_by=current_user.id, dataset_id=dataset_id)
        except ValueError as e:
            flash(str(e), "danger")
            return redirect(url_for("ai.train"))

        log_action("models_trained", f"{len(created)} models trained", user_id=current_user.id)
        best = max(created, key=lambda r: r.f1_score or 0)
        flash(f"Trained {len(created)} models. Best: {best.name} (F1 {best.f1_score}) — now active.", "success")
        return redirect(url_for("ai.models"))

    datasets = Dataset.query.order_by(Dataset.uploaded_at.desc()).all()
    return render_template("ai/train.html", datasets=datasets)


@ai_bp.route("/models")
@login_required
def models():
    all_models = MLModel.query.order_by(MLModel.trained_at.desc()).all()
    for m in all_models:
        m.confusion_matrix = json.loads(m.confusion_matrix_json) if m.confusion_matrix_json else None
        m.feature_importance = json.loads(m.feature_importance_json) if m.feature_importance_json else {}
    active = ml_engine.get_active_model()
    return render_template("ai/models.html", models=all_models, active=active)


@ai_bp.route("/models/<int:model_id>/activate", methods=["POST"])
@login_required
def activate(model_id):
    m = ml_engine.activate_model(model_id)
    log_action("model_activated", m.name, user_id=current_user.id)
    flash(f"{m.name} is now the active detection model.", "success")
    return redirect(url_for("ai.models"))


# ---------------------------------------------------------------------
# Detection + anomalies
# ---------------------------------------------------------------------

@ai_bp.route("/detect", methods=["POST"])
@login_required
def detect():
    result = anomaly_engine.run_detection(server_ids=_visible_server_ids())
    if result["status"] != "ok":
        flash(result["message"], "danger")
    else:
        flash(f"Scanned {result['metrics_scored']} readings across {result['servers_scanned']} servers — "
              f"{result['anomalies_created']} new anomalies flagged.", "success")
    return redirect(url_for("ai.anomalies"))


@ai_bp.route("/anomalies")
@login_required
def anomalies():
    ids = _visible_server_ids()
    severity = request.args.get("severity")
    q = Anomaly.query.filter(Anomaly.server_id.in_(ids)) if ids else Anomaly.query.filter(False)
    if severity:
        q = q.filter_by(severity=severity)
    rows = q.order_by(Anomaly.detected_at.desc()).limit(200).all()

    for a in rows:
        a.recs = Recommendation.query.filter_by(anomaly_id=a.id).all()

    servers_by_id = {s.id: s for s in CloudServer.query.filter(CloudServer.id.in_(ids)).all()} if ids else {}
    return render_template("ai/anomalies.html", anomalies=rows, servers_by_id=servers_by_id)


@ai_bp.route("/anomalies/<int:anomaly_id>/resolve", methods=["POST"])
@login_required
def resolve_anomaly(anomaly_id):
    a = Anomaly.query.get_or_404(anomaly_id)
    a.resolved = True
    a.resolved_at = datetime.utcnow()
    a.resolved_by = current_user.id
    db.session.commit()
    return redirect(url_for("ai.anomalies"))


# ---------------------------------------------------------------------
# Predictions
# ---------------------------------------------------------------------

@ai_bp.route("/predictions")
@login_required
def predictions():
    ids = _visible_server_ids()
    servers = CloudServer.query.filter(CloudServer.id.in_(ids)).all() if ids else []
    return render_template("ai/predictions.html", servers=servers)


@ai_bp.route("/predictions/api/<int:server_id>")
@login_required
def api_predict(server_id):
    server = CloudServer.query.get_or_404(server_id)
    if not (current_user.is_admin or server.owner_id == current_user.id):
        return jsonify({"status": "error", "message": "Not authorized"}), 403
    horizon = request.args.get("horizon_hours", 24, type=int)
    result = prediction_engine.predict_server_metrics(server_id, horizon_hours=horizon)
    return jsonify(result)
