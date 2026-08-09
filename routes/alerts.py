from flask import Blueprint, jsonify, request
from models import AlertLog

alerts_bp = Blueprint("alerts", __name__, url_prefix="/api/alerts")


@alerts_bp.get("")
def list_alerts():
    limit = request.args.get("limit", 50, type=int)
    alerts = AlertLog.query.order_by(AlertLog.created_at.desc()).limit(limit).all()
    return jsonify([a.to_dict() for a in alerts])
