from flask import Blueprint, request, jsonify
from ...database.db import SessionLocal
from ...database.models import User

users_bp = Blueprint("users", __name__)

@users_bp.get("/health")
def health():
    return jsonify(ok=True)

@users_bp.post("")
def create_user():
    data = request.get_json(force=True, silent=False)
    if not data or "username" not in data:
        return jsonify(error="username_required"), 400

    db = SessionLocal()
    try:
        if db.query(User).filter_by(Username=data["username"]).first():
            return jsonify(error="username_taken"), 409

        user = User(
            Username=data["username"],
            Email=data.get("email", f'{data["username"]}@local'),
            PasswordHash=data.get("password_hash", "dev"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return jsonify(UserID=user.UserID, Username=user.Username), 201
    except Exception as e:
        db.rollback()
        return jsonify(error="create_user_failed", detail=str(e)), 400
    finally:
        db.close()
