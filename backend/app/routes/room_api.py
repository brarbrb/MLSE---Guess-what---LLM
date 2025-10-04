from flask import Blueprint, request, jsonify, session
from ...database.db import SessionLocal
from ...database.models import Game, PlayerGame, Round, Guess, User
from ...lm_core.word_loader import WordLoader
from ...extensions import socketio

import datetime as dt
import re
import json

room_bp = Blueprint("room_api", __name__)

# ---------- helpers ----------
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
    return [p.strip() for p in txt.split(",") if p.strip()]

def _round_status(rnd) -> str:
    if not rnd or not rnd.Description:
        return "waiting_description"
    if rnd.Status == "completed":
        return "completed"
    return "active"

# ---------- endpoints ----------
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

        # latest round (by RoundNumber)
        rnd = (
            db.query(Round)
              .filter_by(GameID=game_id)
              .order_by(Round.RoundNumber.desc())
              .first()
        )

        # players with scores (PlayerFinalScore)
        players_rows = (
            db.query(User.Username, PlayerGame.PlayerFinalScore)
              .join(PlayerGame, PlayerGame.UserID == User.UserID)
              .filter(PlayerGame.GameID == game_id)
              .all()
        )
        players = [row[0] for row in players_rows]
        scores  = {row[0]: int(row[1] or 0) for row in players_rows}

        # (simple) turn user: creator (you can rotate later if desired)
        turn_user = db.query(User.Username).filter(User.UserID == game.CreatorID).scalar()

        # winner username (if round completed)
        winner_name = None
        if rnd and rnd.RoundWinnerID:
            winner_name = db.query(User.Username).filter(User.UserID == rnd.RoundWinnerID).scalar()

        forbidden_words = list(rnd.ForbiddenWords or []) if rnd else []
        expose_secret = (uid == game.CreatorID and rnd and not rnd.Description)

        payload = {
            "id": game.GameID,
            "status": _round_status(rnd),  # waiting_description | active | completed
            "description": (rnd.Description if rnd else None),
            "scores": scores,
            "players": players,
            "turn": turn_user,
            "startedAt": (rnd.StartTime.isoformat() + "Z") if (rnd and rnd.Description and rnd.StartTime) else None,
            "winner": winner_name,
            "roundNumber": (rnd.RoundNumber if rnd else 1),
            "totalRounds": game.TotalRounds,
        }

        if expose_secret:
            payload["targetWord"] = rnd.TargetWord
            payload["forbiddenWords"] = forbidden_words

        return jsonify(payload)
    finally:
        db.close()

@room_bp.get("/api/room/<int:game_id>/round/<int:round_no>")
def get_room_round(game_id: int, round_no: int):
    db = _db()
    try:
        uid, err = _require_member(db, game_id)
        if err:
            return err

        game = db.query(Game).get(game_id)
        if not game:
            return jsonify(error="game_not_found"), 404

        rnd = (
            db.query(Round)
              .filter_by(GameID=game_id, RoundNumber=round_no)
              .first()
        )
        if not rnd:
            return jsonify(error="round_not_found"), 404

        players_rows = (
            db.query(User.Username, PlayerGame.PlayerFinalScore)
              .join(PlayerGame, PlayerGame.UserID == User.UserID)
              .filter(PlayerGame.GameID == game_id)
              .all()
        )
        players = [r[0] for r in players_rows]
        scores  = {r[0]: int(r[1] or 0) for r in players_rows}

        winner_name = (
            db.query(User.Username).filter(User.UserID == rnd.RoundWinnerID).scalar()
            if rnd.RoundWinnerID else None
        )

        payload = {
            "id": game.GameID,
            "status": ("completed" if rnd.Status == "completed" else ("active" if rnd.Description else "waiting_description")),
            "description": rnd.Description,
            "scores": scores,
            "players": players,
            "turn": db.query(User.Username).filter(User.UserID == game.CreatorID).scalar(),
            "startedAt": (rnd.StartTime.isoformat() + "Z") if rnd.StartTime else None,
            "winner": winner_name,
            "roundNumber": rnd.RoundNumber,
            "totalRounds": game.TotalRounds,
        }

        if (uid == game.CreatorID) and (not rnd.Description):
            payload["targetWord"] = rnd.TargetWord
            payload["forbiddenWords"] = list(rnd.ForbiddenWords or [])

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

        # Disallow target/forbidden words from appearing as whole words
        norm_desc = _normalize(text)
        norm_target = _normalize(rnd.TargetWord)
        if norm_target and re.search(rf"(?:^| ){re.escape(norm_target)}(?: |$)", norm_desc):
            return jsonify(error="forbidden_word_used", which=rnd.TargetWord), 400
        for w in (rnd.ForbiddenWords or []):
            nw = _normalize(w)
            if nw and re.search(rf"(?:^| ){re.escape(nw)}(?: |$)", norm_desc):
                return jsonify(error="forbidden_word_used", which=w), 400

        rnd.Description = text
        if not rnd.StartTime:
            rnd.StartTime = dt.datetime.utcnow()
        rnd.Status = "active"
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

        # normalize & compare
        target  = _normalize(rnd.TargetWord)
        guess_n = _normalize(guess_raw)
        correct = (guess_n == target)

        # elapsed
        now = dt.datetime.utcnow()
        elapsed_ms = int((now - rnd.StartTime).total_seconds() * 1000) if rnd.StartTime else None

        # persist guess (record points awarded)
        g = Guess(
            GameID=game_id,
            RoundID=rnd.RoundID,
            GuesserID=uid,
            GuessText=guess_raw,
            GuessTime=now,
            ResponseTimeSeconds=(elapsed_ms / 1000.0) if elapsed_ms is not None else 0.0,
            PointsAwarded=100 if correct else 0,
            IsCorrect=bool(correct)
        )
        db.add(g)

        # increment user's total guesses
        pg_this_user = db.query(PlayerGame).filter_by(UserID=uid, GameID=game.GameID).first()
        if pg_this_user is not None:
            pg_this_user.TotalGuesses = (pg_this_user.TotalGuesses or 0) + 1

        if correct and rnd.Status != "completed" and (rnd.RoundWinnerID is None):
            # close the round
            rnd.RoundWinnerID = uid
            rnd.EndTime = now
            rnd.Status = "completed"

            # +100 points to the winner (+1 correct counter)
            pg_row = db.query(PlayerGame).filter_by(UserID=uid, GameID=game.GameID).first()
            if pg_row is not None:
                pg_row.PlayerFinalScore = (pg_row.PlayerFinalScore or 0) + 100
                pg_row.TotalCorrectGuesses = (pg_row.TotalCorrectGuesses or 0) + 1

            # next round or finish game
            if rnd.RoundNumber < game.TotalRounds:
                next_rn = rnd.RoundNumber + 1

                # (simple) next describer: rotate by join order relative to winner (placeholder logic)
                player_ids = [r.UserID for r in db.query(PlayerGame).filter_by(GameID=game.GameID).all()]
                if rnd.RoundWinnerID in player_ids:
                    idx = player_ids.index(rnd.RoundWinnerID)
                else:
                    idx = 0
                next_describer_id = player_ids[(idx + 1) % len(player_ids)] if player_ids else game.CreatorID

                # new word set
                wl = WordLoader()
                target_word = wl.generate_target_word()
                if isinstance(target_word, (list, tuple)) and target_word:
                    target_word = target_word[0]
                target_word = str(target_word or "")
                forbidden_list = wl.generate_forbidden_list(target_word) or []
                if not isinstance(forbidden_list, (list, tuple)):
                    forbidden_list = [str(forbidden_list)]

                new_round = Round(
                    GameID=game.GameID,
                    RoundNumber=next_rn,
                    RoundWinnerID=None,
                    TargetWord=target_word,
                    Description=None,
                    ForbiddenWords=list(forbidden_list),
                    Hints=[],
                    StartTime=None,
                    EndTime=None,
                    MaxRoundTime=rnd.MaxRoundTime,
                    Status="waiting_description",
                    # TurnUserID=next_describer_id  # if/when you add this column
                )
                db.add(new_round)
                game.Status = "active"
            else:
                # last round -> finish game
                game.Status = "completed"
                game.EndedAt = now

            db.commit()

            winner_name = db.query(User.Username).filter(User.UserID == uid).scalar()

            _emit("round:won", {
                "winner": winner_name,
                "word": rnd.TargetWord,
                "elapsedMs": elapsed_ms,
                "roundNumber": rnd.RoundNumber,
                "totalRounds": game.TotalRounds,
                "gameCompleted": (game.Status == "completed")
            }, game.GameID)

            return jsonify(
                correct=True,
                message="🎉 Correct! You won!",
                winner=winner_name,
                elapsedMs=elapsed_ms,
                word=rnd.TargetWord,
                roundNumber=rnd.RoundNumber,
                totalRounds=game.TotalRounds,
                gameCompleted=(game.Status == "completed")
            )
        else:
            db.commit()
            return jsonify(correct=False, message="Nope, try again")
    except Exception as e:
        db.rollback()
        return jsonify(error="guess_failed", detail=str(e)), 400
    finally:
        db.close()
