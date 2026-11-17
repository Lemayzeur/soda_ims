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


@export_bp.get("/irrigation.csv")
def export_irrigation_csv():
    """Download irrigation records as a grouped CSV report."""

    import io
    import csv
    import json
    from datetime import datetime
    from flask import Response

    # Fetch all records.
    logs = (
        IrrigationLog.query
        .order_by(IrrigationLog.timestamp.asc())
        .all()
    )

    # Get field names for all fields represented in the records.
    field_ids = {7}

    fields = (
        Field.query.filter(Field.id.in_(field_ids)).all()
        if field_ids else []
    )

    field_names = {
        field.id: field.name
        for field in fields
    }

    # Group records by pot and VWC values.
    # Records without a pot number remain separate.
    grouped_logs = {}

    status_priority = {
        "completed": 5,
        "running": 4,
        "pending": 3,
        "simulated": 2,
        "rejected": 1,
        "failed": 1,
        "not_executed": 1
    }

    for log in logs:

        pot_number = getattr(log, "pot_number", None)

        if pot_number is None:
            # Preserve older records without a pot number.
            key = ("legacy", log.id)

        else:
            key = (
                pot_number,
                round(log.average_vwc, 3) if log.average_vwc is not None else None,
                round(log.min_vwc, 3) if log.min_vwc is not None else None,
                round(log.max_vwc, 3) if log.max_vwc is not None else None
            )

        existing = grouped_logs.get(key)

        if existing is None:
            grouped_logs[key] = log
        else:
            old_status = (
                getattr(existing, "execution_status", None) or ""
            ).lower()

            new_status = (
                getattr(log, "execution_status", None) or ""
            ).lower()

            old_priority = status_priority.get(old_status, 0)
            new_priority = status_priority.get(new_status, 0)

            # Keep the record with the most advanced execution status.
            if new_priority > old_priority:
                grouped_logs[key] = log

    # Sort grouped records by pot number and timestamp.
    logs = sorted(
        grouped_logs.values(),
        key=lambda log: (
            getattr(log, "pot_number", None) is None,
            getattr(log, "pot_number", None) or 0,
            log.timestamp or datetime.min
        )
    )

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Log ID",
        "Command ID",
        "Date and Time",
        "Field",
        "Field ID",
        "Pot Number",
        "Valve",
        "Decision",
        "Execution Status",
        "Execution Message",
        "Average VWC",
        "Minimum VWC",
        "Maximum VWC",
        "Trigger Threshold",
        "Target VWC",
        "Soil Volume (m3)",
        "System Flow (L/s)",
        "Liters Needed",
        "Actual Liters",
        "Runtime (seconds)",
        "Runtime (hours)",
        "Runtime (minutes)",
        "Irrigation Started",
        "Irrigation Completed",
        "Battery (%)",
        "Raw Port Readings"
    ])

    def format_datetime(value):
        """Format datetime values for Excel-friendly CSV output."""
        if value is None:
            return ""

        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")

        return str(value)

    for log in logs:

        # Runtime in seconds.
        runtime_seconds = getattr(log, "runtime_seconds", None)

        if runtime_seconds is None:
            hours = getattr(log, "runtime_hours", 0) or 0
            minutes = getattr(log, "runtime_minutes", 0) or 0

            runtime_seconds = (hours * 3600) + (minutes * 60)

        # Raw port readings.
        raw_ports = getattr(log, "raw_ports_json", None)

        if raw_ports:
            try:
                if not isinstance(raw_ports, str):
                    raw_ports = json.dumps(raw_ports)
            except (TypeError, ValueError):
                raw_ports = str(raw_ports)

        # Write CSV row.
        writer.writerow([
            log.id,
            getattr(log, "command_id", None),
            format_datetime(log.timestamp),
            field_names.get(log.field_id, "Unknown"),
            log.field_id,
            getattr(log, "pot_number", None),
            getattr(log, "valve", None),
            log.decision,
            getattr(log, "execution_status", None),
            getattr(log, "execution_message", None),
            log.average_vwc,
            log.min_vwc,
            log.max_vwc,
            log.trigger_threshold,
            log.target_vwc,
            log.soil_volume_m3,
            log.system_flow_lps,
            log.liters_needed,
            getattr(log, "actual_liters", None),
            runtime_seconds,
            log.runtime_hours,
            log.runtime_minutes,
            format_datetime(getattr(log, "execution_started_at", None)),
            format_datetime(getattr(log, "execution_completed_at", None)),
            log.battery_percent,
            raw_ports
        ])

    # UTF-8 BOM helps Excel recognize the CSV encoding.
    csv_content = "\ufeff" + output.getvalue()
    output.close()

    filename = (
        f"SoDA_Irrigation_Report_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

    return Response(
        csv_content,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
