from flask import Blueprint, request, jsonify
from models import db, AdminEmail

admins_bp = Blueprint("admins", __name__, url_prefix="/api/admins")


@admins_bp.get("")
def list_admins():
    admins = AdminEmail.query.order_by(AdminEmail.email).all()
    return jsonify([a.to_dict() for a in admins])


@admins_bp.post("")
def add_admin():
    data = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    if not email or "@" not in email:
        return jsonify({"error": "a valid email is required"}), 400
    if AdminEmail.query.filter_by(email=email).first():
        return jsonify({"error": "that email is already in the list"}), 409

    admin = AdminEmail(email=email)
    db.session.add(admin)
    db.session.commit()
    return jsonify(admin.to_dict()), 201


@admins_bp.delete("/<int:admin_id>")
def remove_admin(admin_id):
    admin = AdminEmail.query.get_or_404(admin_id)
    db.session.delete(admin)
    db.session.commit()
    return "", 204
