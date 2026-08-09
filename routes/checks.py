from flask import Blueprint, jsonify
from models import Field
from services.checker import run_check_for_field, run_check_for_all_fields

checks_bp = Blueprint("checks", __name__, url_prefix="/api/check-now")


@checks_bp.post("")
def check_all():
    logs = run_check_for_all_fields()
    return jsonify({"checked": len(logs), "results": [l.to_dict() for l in logs]})


@checks_bp.post("/<int:field_id>")
def check_one(field_id):
    field = Field.query.get_or_404(field_id)
    log = run_check_for_field(field)
    return jsonify(log.to_dict())
