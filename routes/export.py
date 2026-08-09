from flask import Blueprint, Response
from models import Field, IrrigationLog, AlertLog
from services.csv_export import irrigation_logs_to_csv, fields_to_csv, alerts_to_csv

export_bp = Blueprint("export", __name__, url_prefix="/api/export")


def _csv_response(content, filename):
    return Response(
        content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@export_bp.get("/irrigation-log")
def export_irrigation_log():
    logs = IrrigationLog.query.order_by(IrrigationLog.timestamp.desc()).all()
    return _csv_response(irrigation_logs_to_csv(logs), "irrigation_log.csv")


@export_bp.get("/fields")
def export_fields():
    fields = Field.query.order_by(Field.name).all()
    return _csv_response(fields_to_csv(fields), "fields.csv")


@export_bp.get("/alerts")
def export_alerts():
    alerts = AlertLog.query.order_by(AlertLog.created_at.desc()).all()
    return _csv_response(alerts_to_csv(alerts), "alerts.csv")
