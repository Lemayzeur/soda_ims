from flask import Blueprint, jsonify, request
from models import Field, IrrigationLog
from datetime import datetime, timezone
from services.checker import run_check_for_field, run_check_for_all_fields

from random import randrange


api_bp = Blueprint("api", __name__, url_prefix="/api")


# --------------------------------------------------
# GET /next
# Arduino requests the next irrigation command
# --------------------------------------------------
@api_bp.get("/next")
def next_data():
    field_id_arg = request.args.get("field_id")

    if field_id_arg is not None:
        try:
            int(field_id_arg)
        except ValueError:
            return jsonify({"error": "field_id must be an integer."}), 400
        
        field = Field.query.get_or_404(field_id_arg)

    log = run_check_for_field(field)

    if log.decision != "IRRIGATED":
        return

    


    


    DEFAULT_DEVICE_ID = "soda-uno-r4"
    device_id = request.args.get("device_id", DEFAULT_DEVICE_ID).strip()

    command = {
        "id": "soda-test-pot2-" + str(randrange(100, 500)),
        "pot_id": "pot_2",
        "pot_number": 2,
        "valve": 2,
        "seconds": 60,
        "strategy": "smart",
        "reason": "single API integration test",
        "expires_at": 1790000000.0
    }

    print("\n========== ARDUINO COMMAND REQUEST ==========")
    print(f"Time:      {datetime.now(timezone.utc).isoformat()}")
    print(f"Device ID: {device_id}")
    print("Command sent to Arduino:")
    print(command)
    print("=============================================\n")

    return jsonify({"command": command})


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

    print("\n=========== ARDUINO REPORT RECEIVED ==========")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print("Raw JSON received from Arduino:")
    print(data)
    print("==============================================\n")

    return jsonify({
        "ok": True,
        "command_id": data.get("id"),
        "status": data.get("status"),
        "message": "Arduino report received"
    }), 200


# --------------------------------------------------
# GET /commands
# Simple endpoint to check the API
# --------------------------------------------------
@api_bp.get("/commands")
def commands():
    return jsonify({
        "ok": True,
        "message": "SoDA irrigation API is running",
        "endpoints": {
            "next": "/next?device_id=soda-uno-r4",
            "report": "/report",
            "commands": "/commands"
        }
    })