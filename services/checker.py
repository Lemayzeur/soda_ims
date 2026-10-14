import json
from datetime import datetime, timedelta

from models import db, IrrigationLog, AlertLog, AdminEmail
from services.zentra_client import fetch_field_readings
from services.calculations import evaluate_field
from services.email_service import send_irrigation_alert_email, send_sensor_warning_email

LOW_BATTERY_THRESHOLD = 20


def run_check_for_field(field):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=field.check_frequency_days)

    logger_readings = fetch_field_readings(field, start_date, end_date)
    evaluation = evaluate_field(field, logger_readings)

    log_entry = IrrigationLog(
        field_id=field.id,
        timestamp=end_date,
        decision=evaluation["decision"],
        average_vwc=evaluation["average_vwc"],
        min_vwc=evaluation["min_vwc"],
        max_vwc=evaluation["max_vwc"],
        num_ports_reporting=evaluation["num_ports_reporting"],
        num_ports_below_threshold=evaluation["num_ports_below_threshold"],
        num_ports_error=evaluation["num_ports_error"],
        trigger_threshold=field.trigger_threshold,
        target_vwc=field.target_vwc,
        soil_volume_m3=field.soil_volume_m3,
        system_flow_lps=field.system_flow_lps,
        vwc_deficit=evaluation["vwc_deficit"],
        liters_needed=evaluation["liters_needed"],
        runtime_hours=evaluation["runtime_hours"],
        runtime_minutes=evaluation["runtime_minutes"],
        battery_percent=evaluation["battery_percent"],
        raw_ports_json=json.dumps(logger_readings),
    )
    db.session.add(log_entry)

    admin_emails = [a.email for a in AdminEmail.query.all()]
    low_battery = evaluation["battery_percent"] is not None and evaluation["battery_percent"] < LOW_BATTERY_THRESHOLD

    if evaluation["decision"] == "IRRIGATED":
        message = (
            f"Needs ~{evaluation['liters_needed']} L, run "
            f"{evaluation['runtime_hours']}h {evaluation['runtime_minutes']}m "
            f"({evaluation['num_ports_below_threshold']} of {evaluation['num_ports_reporting']} ports below threshold)."
        )
        sent = send_irrigation_alert_email(field, evaluation, logger_readings, admin_emails, end_date)
        db.session.add(AlertLog(
            field_id=field.id,
            alert_type="IRRIGATION",
            message=message,
            sent_to=json.dumps(admin_emails if sent else []),
        ))

    elif evaluation["num_ports_error"] > 0 or low_battery:
        parts = []
        if evaluation["num_ports_error"] > 0:
            parts.append(f"{evaluation['num_ports_error']} port(s) not reporting")
        if low_battery:
            parts.append(f"battery at {evaluation['battery_percent']}%")
        message = ", ".join(parts)

        sent = send_sensor_warning_email(field, evaluation, logger_readings, admin_emails, message)
        db.session.add(AlertLog(
            field_id=field.id,
            alert_type="SENSOR_WARNING",
            message=message,
            sent_to=json.dumps(admin_emails if sent else []),
        ))

    db.session.commit()
    return log_entry


def run_check_for_all_fields():
    from models import Field
    return [run_check_for_field(field) for field in Field.query.all()]
