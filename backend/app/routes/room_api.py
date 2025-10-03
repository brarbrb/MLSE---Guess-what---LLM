from flask import Blueprint, request, jsonify, session
from ...database.db import SessionLocal
from ...database.models import Game, PlayerGame, Round, Guess, User
from ...lm_core.word_loader import WordLoader
import datetime as dt
import re
import json
from ...extensions import socketio
        
        
room_bp = Blueprint("room_api", __name__)

def _db():
    return SessionLocal()

def _require_member(db, game_id):
    uid = session.get("user_id")
    if not uid:
        return None, (jsonify(error="not_logged_in"), 401)
    in_game = db.query(PlayerGame).filter_by(UserID=uid, GameID=game_id).first()
    if not in_game:
        return None, (jsonify(error="not_in_game"), 403)
    return uid, None

_ws_re = re.compile(r"\s+")
def _normalize(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^\w\s]", " ", s)
    return _ws_re.sub(" ", s).strip()

def _emit(event, data, game_id):
    if socketio:
        socketio.emit(event, data, to=f"game-{game_id}")

def _parse_forbidden(raw):
    """ForbiddenWords might be stored as JSON text (recommended) or comma string."""
    if not raw:
        return []
    if isinstance(raw, (list, tuple)):
        return list(raw)
    txt = str(raw).strip()
    try:
        v = json.loads(txt)
        if isinstance(v, list):
            return [str(x) for x in v]
    except Exception:
        pass
    # fallback: split by comma
    return [p.strip() for p in txt.split(",") if p.strip()]

def _round_status(rnd) -> str:
    if not rnd:
        return "waiting_description"
    if not rnd.Description:
        return "waiting_description"
    if rnd.Status == "completed":
        return "completed"
    return "active"

@room_bp.get("/api/room/<int:game_id>")
def get_room(game_id: int):
    db = _db()
    try:
        uid, err = _require_member(db, game_id)
        if err:
            return err

        game = db.query(Game).get(game_id)
        if not game:
            return jsonify(error="game_not_found"), 404

        # latest round (single-round v1)
        rnd = (
            db.query(Round)
            .filter_by(GameID=game_id)
            .order_by(Round.RoundNumber.desc())   # adjust if your column name differs
            .first()
        )

        # players (for left list and zeroed scores)
        players_rows = (
            db.query(User.Username)
            .join(PlayerGame, PlayerGame.UserID == User.UserID)
            .filter(PlayerGame.GameID == game_id)
            .all()
        )
        players = [name for (name,) in players_rows]
        scores  = {name: 0 for name in players}  # you can replace with real per-game scores later

        # turn is the creator for v1 (describer)
        turn_user = db.query(User.Username).filter(User.UserID == game.CreatorID).scalar()

        # winner username if completed
        winner_name = None
        if rnd and rnd.RoundWinnerID:
            winner_name = db.query(User.Username).filter(User.UserID == rnd.RoundWinnerID).scalar()

        # forbidden list (only expose to creator before description is submitted)
        # forbidden_words = _parse_forbidden(rnd.ForbiddenWords) if rnd else []
        forbidden_words = list(rnd.ForbiddenWords or []) if rnd else []
        expose_secret = (uid == game.CreatorID and rnd and not rnd.Description)

        payload = {
            "id": game.GameID,
            "status": _round_status(rnd),  # waiting_description | active | completed
            "description": (rnd.Description if rnd else None),
            "scores": scores,              # room.js: updateScores()
            "players": players,            # for #players-list
            "turn": turn_user,             # room.js toggles sections by this
            "startedAt": (rnd.StartTime.isoformat() + "Z") if (rnd and rnd.Description and rnd.StartTime) else None,
            "winner": winner_name,
        }

        if expose_secret:
            payload["targetWord"] = rnd.TargetWord
            payload["forbiddenWords"] = forbidden_words

        return jsonify(payload)
    finally:
        db.close()

@room_bp.put("/api/room/<int:game_id>/description")
def put_description(game_id: int):
    db = _db()
    try:
        uid, err = _require_member(db, game_id)
        if err:
            return err

        game = db.query(Game).get(game_id)
        if not game:
            return jsonify(error="game_not_found"), 404
        if uid != game.CreatorID:
            return jsonify(error="not_creator"), 403

        rnd = (
            db.query(Round)
            .filter_by(GameID=game_id)
            .order_by(Round.RoundNumber.desc())
            .first()
        )
        if not rnd:
            return jsonify(error="round_missing"), 400
        if rnd.Description:
            return jsonify(error="already_described"), 409

        data = request.get_json(force=True) or {}
        text = (data.get("description") or "").strip()
        if not text:
            return jsonify(error="empty_description"), 400

        # Minimal validity check: no target word or forbidden words as whole words
        wl = WordLoader()  # you can remove if not needed; mock is present anyway
        norm_desc = _normalize(text)
        norm_target = _normalize(rnd.TargetWord)
        if norm_target and re.search(rf"(?:^| ){re.escape(norm_target)}(?: |$)", norm_desc):
            return jsonify(error="forbidden_word_used", which=rnd.TargetWord), 400

        forb = _parse_forbidden(rnd.ForbiddenWords)
        for w in (rnd.ForbiddenWords or []):
            nw = _normalize(w)
            if nw and re.search(rf"(?:^| ){re.escape(nw)}(?: |$)", norm_desc):
                return jsonify(error="forbidden_word_used", which=w), 400

        # Accept description
        rnd.Description = text
        if not rnd.StartTime:
            rnd.StartTime = dt.datetime.utcnow()
        rnd.Status = "active"    # <-- make it explicit
        db.commit()
        # Keep rnd.Status as "active" — it becomes "completed" when someone guesses
        db.commit()
        _emit("round:description", {
            "description": rnd.Description,
            "startedAt": rnd.StartTime.isoformat() + "Z"
        }, game_id)
        return jsonify(ok=True, message="Description accepted", startedAt=rnd.StartTime.isoformat() + "Z")
    except Exception as e:
        db.rollback()
        return jsonify(error="desc_failed", detail=str(e)), 400
    finally:
        db.close()

@room_bp.put("/api/room/<int:game_id>/guess")
def put_guess(game_id: int):
    db = _db()
    try:
        uid, err = _require_member(db, game_id)
        if err:
            return err

        game = db.query(Game).get(game_id)
        if not game:
            return jsonify(error="game_not_found"), 404
        if uid == game.CreatorID:
            return jsonify(error="creator_cannot_guess"), 403
        
        rnd = (
            db.query(Round)
            .filter_by(GameID=game_id)
            .order_by(Round.RoundNumber.desc())
            .first()
        )
        if not rnd or not rnd.Description:
            return jsonify(error="round_not_ready", message="Wait for the description"), 400

        data = request.get_json(force=True) or {}
        guess_raw = (data.get("guess") or "").strip()
        if not guess_raw:
            return jsonify(error="empty_guess"), 400

        # Normalize & compare
        target = _normalize(rnd.TargetWord)
        guess  = _normalize(guess_raw)
        correct = (guess == target)

        # Compute response time if possible
        now = dt.datetime.utcnow()
        elapsed_ms = None
        if rnd.StartTime:
            elapsed_ms = int((now - rnd.StartTime).total_seconds() * 1000)

        # Persist the guess
        g = Guess(
            GameID=game_id,
            RoundID=rnd.RoundID,
            GuesserID=uid,
            GuessText=guess_raw,
            ResponseTimeSeconds=(elapsed_ms / 1000.0) if elapsed_ms is not None else 0.0,
            IsCorrect=bool(correct)
        )
        db.add(g)

        if correct and rnd.Status != "completed" and (rnd.RoundWinnerID is None):
            # finalize the round
            rnd.RoundWinnerID = uid
            rnd.EndTime = now
            rnd.Status = "completed"
            # (optional) also mark game completed if single-round
            # game.Status = "completed"

            db.commit()

            winner_name = db.query(User.Username).filter(User.UserID == uid).scalar()

            # ⬇️ EMIT ONLY ON CORRECT
            _emit("round:won", {
                "winner": winner_name,
                "word": rnd.TargetWord,
                "elapsedMs": elapsed_ms
            }, game_id)

            return jsonify(
                correct=True,
                message="🎉 Correct! You won!",
                winner=winner_name,
                elapsedMs=elapsed_ms,
                word=rnd.TargetWord
            )
        else:
            # incorrect guess: just store and return
            db.commit()
            return jsonify(correct=False, message="Nope, try again")

    except Exception as e:
        db.rollback()
        return jsonify(error="guess_failed", detail=str(e)), 400
    finally:
        db.close()
