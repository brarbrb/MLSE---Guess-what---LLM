from flask import Blueprint, request, jsonify
from ...database.db import SessionLocal
from ...database.models import User, Game, GameSettings

games_bp = Blueprint("games", __name__)

@games_bp.post("")
def create_game():
    data = request.get_json(force=True)
    required = ("creator_username", "game_code", "total_rounds")
    if any(k not in data for k in required):
        return jsonify(error="missing_fields", required=required), 400

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(Username=data["creator_username"]).first()
        if not user:
            return jsonify(error="creator_not_found"), 404

        game = Game(
            CreatorID=user.UserID,
            GameCode=data["game_code"],
            TotalRounds=int(data["total_rounds"]),
            MaxPlayers=int(data.get("max_players", 5)),
        )
        db.add(game)
        db.flush()
        db.add(GameSettings(GameID=game.GameID))  # defaults
        db.commit()
        return jsonify(GameID=game.GameID, GameCode=game.GameCode), 201
    except Exception as e:
        db.rollback()
        return jsonify(error="create_game_failed", detail=str(e)), 400
    finally:
        db.close()
