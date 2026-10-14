from flask import Blueprint, jsonify
from models import Field, IrrigationLog

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.get("")
def get_dashboard():
    fields = Field.query.order_by(Field.created_at).all()
    rows = []
    needs_water = 0
    ok_count = 0
    issue_count = 0

    for field in fields:
        latest = (
            IrrigationLog.query.filter_by(field_id=field.id)
            .order_by(IrrigationLog.timestamp.desc())
            .first()
        )
        rows.append({
            "field": field.to_dict(include_loggers=True),
            "latest": latest.to_dict() if latest else None,
        })

        if latest:
            if latest.decision == "IRRIGATED":
                needs_water += 1
            elif latest.decision == "OK":
                ok_count += 1
            elif latest.decision in ("PARTIAL", "NO_DATA"):
                issue_count += 1

    return jsonify({
        "summary": {
            "total_fields": len(fields),
            "needs_water": needs_water,
            "ok": ok_count,
            "issues": issue_count,
        },
        "fields": rows,
    })
