from flask import Blueprint, jsonify, request
from models import db, Field, IrrigationLog
from datetime import datetime, timezone
from services.checker import run_check_for_field, run_check_for_all_fields

from datetime import datetime, timedelta
from services.zentra_client import fetch_field_readings
from services.calculations import evaluate_field
from services.email_service import send_irrigation_alert_email, send_sensor_warning_email

from random import randrange
from uuid import uuid4

api_bp = Blueprint("api", __name__, url_prefix="/api")


# --------------------------------------------------
# GET /commands
# Arduino requests the irrigation commands
# --------------------------------------------------
@api_bp.get("/commands")
def get_commands():
    field_id_arg = request.args.get("field_id")
    pot_number_arg = request.args.get("pot_number")

    if field_id_arg is None:
        return jsonify({'error': 'field_id not provided'}), 400
    try:
        int(field_id_arg)
    except ValueError:
        return jsonify({"error": "field_id must be an integer."}), 400
    
    field = Field.query.get_or_404(field_id_arg)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=field.check_frequency_days)

    logger_readings = fetch_field_readings(field, start_date, end_date)
    evaluation = evaluate_field(field, logger_readings)
    
    # log = run_check_for_field(field)

    # if log.decision != "IRRIGATED":
        # return
    port_decisions = evaluation.get("port_decisions", [])

    if pot_number_arg is not None:
        try:
            requested_pot = int(pot_number_arg)
        except ValueError:
            return jsonify({"error": "pot_number must be an integer"}), 400

        port_decisions = [
            p for p in port_decisions
            if p.get("pot_number") == requested_pot
        ]


    commands = []

    for pot in port_decisions:
        if not pot.get("needs_irrigation"):
            continue

        if pot.get("status") != "IRRIGATION_NEEDED":
            continue

        seconds = pot.get("seconds")

        if not isinstance(seconds, (int, float)) or seconds <= 0:
            continue

        pot_number = pot["pot_number"]
        valve = pot["valve"]
        vwc = pot["vwc"]

        command_id = f"soda-ims-pot{pot_number}-{uuid4().hex}"

        command = {
            "id": command_id,
            "pot_id": f"pot_{pot_number}",
            "pot_number": pot_number,
            "valve": valve,
            "seconds": int(seconds),
            "strategy": "smart",
             "reason": (
                f"VWC {vwc:.3f} below greenhouse "
                f"start threshold {field.trigger_threshold:.2f}"
            ),
            "expires_at": datetime.now(timezone.utc).timestamp() + 300
        }

        commands.append(command)

        # Save the irrigation decision and pending execution status.
        log_entry = IrrigationLog(
            field_id=field.id,
            timestamp=datetime.now(),
            decision="IRRIGATION_NEEDED",

            # Store the individual pot's reading.
            average_vwc=vwc,
            min_vwc=vwc,
            max_vwc=vwc,

            # Store this command's calculated irrigation amount/runtime.
            liters_needed=pot.get("liters_needed"),
            runtime_seconds=int(seconds),
            runtime_hours=int(seconds) // 3600,
            runtime_minutes=(int(seconds) % 3600) // 60,

            # Link the database record to the Arduino command.
            command_id=command_id,
            pot_number=pot_number,
            valve=valve,
            execution_status="pending",
            execution_message="Command created; awaiting Arduino execution."
        )

        db.session.add(log_entry)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    print({"commands": commands})
    return jsonify({"commands": commands})


# --------------------------------------------------
# POST /report
# Arduino reports command status and flow readings
# --------------------------------------------------
@api_bp.post("/report")
def report_data():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "ok": False,
            "message": "Expected a JSON object"
        }), 400

    command_id = data.get("id")
    status = data.get("status")
    message = data.get("message") or data.get("reason")

    if not command_id or not status:
        return jsonify({
            "ok": False,
            "message": "Both id and status are required"
        }), 400

    log_entry = IrrigationLog.query.filter_by(
        command_id=command_id
    ).first()

    if log_entry is None:
        return jsonify({
            "ok": False,
            "message": "No irrigation log found for this command ID"
        }), 404

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    log_entry.execution_status = status
    log_entry.execution_message = message

    if status == "running":
        log_entry.execution_started_at = now

    elif status == "completed":
        log_entry.execution_completed_at = now

    # Save actual volume if Arduino includes it in its report.
    actual_liters = data.get("total_liters")
    if actual_liters is not None:
        try:
            log_entry.actual_liters = float(actual_liters)
        except (TypeError, ValueError):
            return jsonify({
                "ok": False,
                "message": "total_liters must be numeric"
            }), 400

    db.session.commit()

    print(
        f"Arduino command {command_id}: "
        f"{status} — {message}"
    )

    return jsonify({
        "ok": True,
        "command_id": command_id,
        "status": log_entry.execution_status,
        "message": "Irrigation execution status saved"
    }), 200