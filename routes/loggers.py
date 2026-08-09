from flask import Blueprint, request, jsonify
from models import db, Logger

loggers_bp = Blueprint("loggers", __name__, url_prefix="/api/loggers")


@loggers_bp.put("/<int:logger_id>")
def update_logger(logger_id):
    logger = Logger.query.get_or_404(logger_id)
    data = request.get_json(force=True) or {}

    if "serial_number" in data:
        serial_number = data["serial_number"].strip()
        if not serial_number:
            return jsonify({"error": "serial_number cannot be empty"}), 400
        logger.serial_number = serial_number

    if "port_mode" in data:
        if data["port_mode"] not in ("include", "exclude"):
            return jsonify({"error": "port_mode must be 'include' or 'exclude'"}), 400
        logger.port_mode = data["port_mode"]

    if "ports" in data:
        logger.set_ports(data["ports"])

    db.session.commit()
    return jsonify(logger.to_dict())


@loggers_bp.delete("/<int:logger_id>")
def delete_logger(logger_id):
    logger = Logger.query.get_or_404(logger_id)
    db.session.delete(logger)
    db.session.commit()
    return "", 204
