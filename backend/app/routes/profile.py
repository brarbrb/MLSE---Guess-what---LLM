from flask import Blueprint, jsonify, session
from ...database.db import SessionLocal
from ...database.models import User, Game, Round, Guess, PlayerGame
from sqlalchemy import func

profile_bp = Blueprint("profile", __name__)

def _db():
    return SessionLocal()

@profile_bp.get("/api/profile/summary")
def profile_summary():
    uid = session.get("user_id")
    if not uid:
        return jsonify(error="not_logged_in"), 401

    db = _db()
    try:
        # some basic stats
        total_games = (
            db.query(func.count(PlayerGame.PlayerGameID))
              .filter(PlayerGame.UserID == uid)
              .scalar()
        )
        total_score = (
            db.query(func.coalesce(func.sum(PlayerGame.PlayerFinalScore), 0))
              .filter(PlayerGame.UserID == uid)
              .scalar()
        )

        base = (
            db.query(
                Guess.ResponseTimeSeconds.label("secs"),
                Round.TargetWord.label("word"),
                Round.RoundNumber.label("round_no"),
                Game.GameID.label("game_id"),
                Game.GameCode.label("game_code"),
                Guess.GuessTime.label("when_ts")
            )
            .join(Round, Round.RoundID == Guess.RoundID)
            .join(Game,  Game.GameID  == Guess.GameID)
            .filter(Guess.GuesserID == uid, Guess.IsCorrect == True)
        )

        fastest = (
            base.order_by("secs")
                .limit(3)
                .all()
        )

        hardest = ( # longest time to answer correctly
            base.order_by(func.coalesce(Guess.ResponseTimeSeconds, 0).desc())
                .limit(3)
                .all()
        )

        def _row_to_dict(r):
            return {
                "word": r.word,
                "response_sec": float(r.secs or 0.0),
                "game_id": r.game_id,
                "game_code": r.game_code,
                "round_no": r.round_no,
                "when": r.when_ts.isoformat() + "Z" if r.when_ts else None
            }

        return jsonify(
            ok=True,
            totals={
                "total_games": int(total_games or 0),
                "total_score": int(total_score or 0)
            },
            fastest=[_row_to_dict(x) for x in fastest],
            hardest=[_row_to_dict(x) for x in hardest]
        )
    finally:
        db.close()
