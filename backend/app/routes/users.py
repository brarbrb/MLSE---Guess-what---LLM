from flask import Blueprint, request, jsonify
from sqlalchemy import or_
from ...database.db import SessionLocal
from ...database.models import User

users_bp = Blueprint("users", __name__)

@users_bp.get("/health")
def health():
    return jsonify(ok=True)

@users_bp.post("")
def create_user():
    data = request.get_json(silent=True) or {}

    uname = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    pw    = (data.get("password_hash") or "")

    # Required fields
    if not uname:
        return jsonify(error="username_required"), 400
    if not email:
        return jsonify(error="email_required"), 400
    if not pw:
        return jsonify(error="password_required"), 400

    MAX_USERNAME = 50
    MAX_EMAIL = 255
    MIN_PASSWORD = 6
    MAX_PASSWORD = 128

    if len(uname) > MAX_USERNAME:
        return jsonify(error="username_too_long"), 422
    if len(email) > MAX_EMAIL:
        return jsonify(error="email_too_long"), 422
    if len(pw) < MIN_PASSWORD:
        return jsonify(error="password_too_short"), 422
    if len(pw) > MAX_PASSWORD:
        return jsonify(error="password_too_long"), 422

    # Email format rules
    if email.count("@") != 1:
        return jsonify(error="invalid_email"), 422
    local, domain = email.split("@", 1)
    if not local or not domain:
        return jsonify(error="invalid_email"), 422
    if not email.endswith(".com"):
        return jsonify(error="invalid_email_suffix"), 422

    # uniqueness checks before insert
    db = SessionLocal()
    try:
        exists = db.query(User).filter(or_(User.Username == uname, User.Email == email)).first()
        if exists:
            if exists.Username == uname:
                return jsonify(error="username_taken"), 409
            if exists.Email == email:
                return jsonify(error="email_taken"), 409
            return jsonify(error="conflict"), 409

        user = User(Username=uname, Email=email, PasswordHash=pw)
        db.add(user)
        db.commit()
        db.refresh(user)
        return jsonify(UserID=user.UserID, Username=user.Username), 201

    except Exception:
        db.rollback()
        return jsonify(error="create_user_failed"), 400
    finally:
        db.close()
