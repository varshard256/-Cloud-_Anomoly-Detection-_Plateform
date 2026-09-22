from datetime import datetime

from app.extensions import db


class Dataset(db.Model):
    __tablename__ = "datasets"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)

    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    row_count = db.Column(db.Integer, default=0)
    column_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="uploaded")  # uploaded|validated|cleaned|trained

    models = db.relationship("MLModel", backref="dataset", lazy="dynamic")


class MLModel(db.Model):
    __tablename__ = "ml_models"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    model_type = db.Column(db.String(50), nullable=False)  # isolation_forest|random_forest|one_class_svm|lof
    dataset_id = db.Column(db.Integer, db.ForeignKey("datasets.id"), nullable=True)
    trained_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    trained_at = db.Column(db.DateTime, default=datetime.utcnow)

    file_path = db.Column(db.String(255), nullable=False)

    accuracy = db.Column(db.Float)
    precision_score = db.Column(db.Float)
    recall_score = db.Column(db.Float)
    f1_score = db.Column(db.Float)
    roc_auc = db.Column(db.Float)

    confusion_matrix_json = db.Column(db.Text)   # JSON-encoded 2x2 matrix
    feature_importance_json = db.Column(db.Text)  # JSON-encoded {feature: importance}

    is_active = db.Column(db.Boolean, default=False)  # currently used for live detection

    def __repr__(self):
        return f"<MLModel {self.name} ({self.model_type})>"


class Prediction(db.Model):
    __tablename__ = "predictions"

    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey("cloud_servers.id"), nullable=False)
    predicted_at = db.Column(db.DateTime, default=datetime.utcnow)

    metric_type = db.Column(db.String(50), nullable=False)  # cpu_usage|memory_usage|disk_usage
    horizon_hours = db.Column(db.Integer, default=24)
    predicted_value = db.Column(db.Float, nullable=False)
    actual_value = db.Column(db.Float, nullable=True)

    failure_probability = db.Column(db.Float, default=0)


class Report(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    report_type = db.Column(db.String(10), nullable=False)  # pdf|excel|csv
    file_path = db.Column(db.String(255), nullable=False)

    generated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SystemLog(db.Model):
    __tablename__ = "system_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(255))
    level = db.Column(db.String(20), default="info")  # info|warning|error
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
