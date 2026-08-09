from flask import Blueprint, jsonify
from models import Field
from services.forecast_service import get_forecast_template

forecast_bp = Blueprint("forecast", __name__, url_prefix="/api/forecast")


@forecast_bp.get("/<int:field_id>")
def get_forecast(field_id):
    field = Field.query.get_or_404(field_id)
    return jsonify(get_forecast_template(field))
