from datetime import datetime
from flask import Blueprint, request, jsonify
from models import db, Field, Logger

fields_bp = Blueprint("fields", __name__, url_prefix="/api/fields")


def _parse_start_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


@fields_bp.get("")
def list_fields():
    fields = Field.query.order_by(Field.name).all()
    return jsonify([f.to_dict() for f in fields])


@fields_bp.post("")
def create_field():
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    if Field.query.filter_by(name=name).first():
        return jsonify({"error": "a field with that name already exists"}), 409

    field = Field(
        name=name,
        trigger_threshold=data.get("trigger_threshold", 0.229),
        target_vwc=data.get("target_vwc", 0.32),
        soil_volume_m3=data.get("soil_volume_m3", 1.002),
        system_flow_lps=data.get("system_flow_lps", 0.00244),
        check_frequency_days=data.get("check_frequency_days", 5),
        start_date=_parse_start_date(data.get("start_date")),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
    )
    db.session.add(field)
    db.session.commit()
    return jsonify(field.to_dict()), 201


@fields_bp.get("/<int:field_id>")
def get_field(field_id):
    field = Field.query.get_or_404(field_id)
    return jsonify(field.to_dict())


@fields_bp.put("/<int:field_id>")
def update_field(field_id):
    field = Field.query.get_or_404(field_id)
    data = request.get_json(force=True) or {}

    if "name" in data:
        new_name = data["name"].strip()
        clash = Field.query.filter(Field.name == new_name, Field.id != field_id).first()
        if clash:
            return jsonify({"error": "a field with that name already exists"}), 409
        field.name = new_name

    for attr in ["trigger_threshold", "target_vwc", "soil_volume_m3",
                 "system_flow_lps", "check_frequency_days", "latitude", "longitude"]:
        if attr in data:
            setattr(field, attr, data[attr])

    if "start_date" in data:
        field.start_date = _parse_start_date(data["start_date"])

    db.session.commit()
    return jsonify(field.to_dict())


@fields_bp.delete("/<int:field_id>")
def delete_field(field_id):
    field = Field.query.get_or_404(field_id)
    db.session.delete(field)
    db.session.commit()
    return "", 204


# --- Loggers nested under a field ---

@fields_bp.post("/<int:field_id>/loggers")
def add_logger(field_id):
    field = Field.query.get_or_404(field_id)
    data = request.get_json(force=True) or {}
    serial_number = (data.get("serial_number") or "").strip()
    if not serial_number:
        return jsonify({"error": "serial_number is required"}), 400

    port_mode = data.get("port_mode", "include")
    if port_mode not in ("include", "exclude"):
        return jsonify({"error": "port_mode must be 'include' or 'exclude'"}), 400

    logger = Logger(field_id=field.id, serial_number=serial_number, port_mode=port_mode)
    logger.set_ports(data.get("ports", []))
    db.session.add(logger)
    db.session.commit()
    return jsonify(logger.to_dict()), 201
