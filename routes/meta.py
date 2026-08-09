from flask import Blueprint, jsonify
from services.tz_utils import COMMON_TIMEZONES

meta_bp = Blueprint("meta", __name__, url_prefix="/api")


@meta_bp.get("/timezones")
def list_timezones():
    return jsonify(COMMON_TIMEZONES)
