"""
Report Engine
----------------
Generates downloadable reports (CSV, Excel, PDF) summarizing anomalies,
server health, and detection accuracy — for the Reports module.
"""

import os
from datetime import datetime

import pandas as pd
from flask import current_app
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from app.models import Anomaly, CloudServer, MLModel


def _gather_anomaly_rows(server_ids=None):
    q = Anomaly.query
    if server_ids:
        q = q.filter(Anomaly.server_id.in_(server_ids))
    rows = q.order_by(Anomaly.detected_at.desc()).limit(500).all()
    data = []
    for a in rows:
        server = CloudServer.query.get(a.server_id)
        data.append({
            "Detected At": a.detected_at.strftime("%Y-%m-%d %H:%M"),
            "Server": server.name if server else f"#{a.server_id}",
            "Type": a.anomaly_type,
            "Severity": a.severity,
            "Risk Score": a.anomaly_score,
            "Model": a.model_used,
            "Resolved": "Yes" if a.resolved else "No",
        })
    return data


def generate_csv(server_ids=None) -> str:
    data = _gather_anomaly_rows(server_ids)
    df = pd.DataFrame(data)
    filename = f"anomaly_report_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.csv"
    path = os.path.join(current_app.config["REPORT_FOLDER"], filename)
    df.to_csv(path, index=False)
    return path


def generate_excel(server_ids=None) -> str:
    data = _gather_anomaly_rows(server_ids)
    df = pd.DataFrame(data)
    filename = f"anomaly_report_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.xlsx"
    path = os.path.join(current_app.config["REPORT_FOLDER"], filename)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Anomalies")
    return path


def generate_pdf(server_ids=None) -> str:
    data = _gather_anomaly_rows(server_ids)
    filename = f"anomaly_report_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
    path = os.path.join(current_app.config["REPORT_FOLDER"], filename)

    doc = SimpleDocTemplate(path, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("NeuroCloud — Anomaly Report", styles["Title"]),
        Paragraph(f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]),
        Spacer(1, 0.5 * cm),
    ]

    active = MLModel.query.filter_by(is_active=True).first()
    if active:
        elements.append(Paragraph(
            f"Active detection model: {active.name} — F1 {active.f1_score}, "
            f"Precision {active.precision_score}, Recall {active.recall_score}", styles["Normal"]))
        elements.append(Spacer(1, 0.4 * cm))

    if data:
        table_data = [list(data[0].keys())] + [[str(v) for v in row.values()] for row in data[:100]]
        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#131B2E")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ]))
        elements.append(table)
    else:
        elements.append(Paragraph("No anomalies recorded yet.", styles["Normal"]))

    doc.build(elements)
    return path


GENERATORS = {"csv": generate_csv, "excel": generate_excel, "pdf": generate_pdf}
