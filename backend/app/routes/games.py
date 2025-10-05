from flask import Blueprint, request, jsonify, session
from ...database.db import SessionLocal
from ...database.models import User, Game, GameSettings, PlayerGame, Round
from sqlalchemy import func
from ...extensions import socketio

import random
import string
import datetime as dt
import json

# Word source (your mock for now)
from ...lm_core.word_loader import WordLoader

games_bp = Blueprint("games", __name__)

# --- helpers ---
def _db():
    return SessionLocal()

def _require_login():
    uid = session.get("user_id")
    if not uid:
        return None, (jsonify(error="not_logged_in"), 401)
    return uid, None

def _gen_code(n=6):
    # 6-char uppercase code
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=n))

# --- Create game (+ settings) ---
@games_bp.post("")
def create_game():
    uid, err = _require_login()
    if err:
        return err
    data = request.get_json(force=True)

    # payload: { round_time, difficulty, allow_hints, max_hints, max_players, is_private, total_rounds }
    round_time   = int(data.get("round_time", 180))
    difficulty   = (data.get("difficulty") or "medium").lower()
    allow_hints  = bool(data.get("allow_hints", True))
    max_hints    = int(data.get("max_hints", 3))
    max_players  = int(data.get("max_players", 5))
    total_rounds = int(data.get("total_rounds", 6))
    is_private   = bool(data.get("is_private", False))

    if difficulty not in ("easy", "medium", "hard"):
        return jsonify(error="bad_difficulty"), 400
    if not (3 <= max_players <= 10):
        return jsonify(error="bad_max_players"), 400

    db = _db()
    try:
        # ensure user exists
        user = db.query(User).get(uid)
        if not user:
            return jsonify(error="user_missing"), 400

        # unique GameCode
        for _ in range(12):
            code = _gen_code(6)
            if not db.query(Game).filter_by(GameCode=code).first():
                break
        else:
            return jsonify(error="code_gen_failed"), 500

        game = Game(
            CreatorID=user.UserID,
            GameCode=code,
            TotalRounds=total_rounds,
            MaxPlayers=max_players,
            IsPrivate=is_private,
            Status="waiting",
            CurrentPlayersCount=1,
        )
        db.add(game)
        db.flush()  # get GameID

        # 1:1 settings
        settings = GameSettings(
            GameID=game.GameID,
            RoundTimeSeconds=round_time,
            DifficultyLevel=difficulty,
            AllowHints=allow_hints,
            MaxHintsPerRound=max_hints,
        )
        db.add(settings)

        # add creator as first player
        db.add(PlayerGame(UserID=user.UserID, GameID=game.GameID))

        db.commit()
        return jsonify(
            ok=True,
            game_id=game.GameID,
            game_code=game.GameCode,
            status=game.Status,
            is_private=game.IsPrivate
        ), 201
    except Exception as e:
        db.rollback()
        return jsonify(error="create_game_failed", detail=str(e)), 400
    finally:
        db.close()

# --- Join by code (private) ---
@games_bp.post("/join_by_code")
def join_by_code():
    uid, err = _require_login()
    if err:
        return err
    code = (request.get_json(force=True).get("game_code") or "").upper().strip()
    if not code:
        return jsonify(error="code_required"), 400

    db = _db()
    try:
        game = db.query(Game).filter_by(GameCode=code).first()
        if not game or game.Status != "waiting":
            return jsonify(error="not_joinable"), 400
        if game.CurrentPlayersCount >= game.MaxPlayers:
            return jsonify(error="room_full"), 409

        # add player if not already in
        if not db.query(PlayerGame).filter_by(UserID=uid, GameID=game.GameID).first():
            db.add(PlayerGame(UserID=uid, GameID=game.GameID))
            game.CurrentPlayersCount += 1

        db.commit()
        return jsonify(ok=True, game_id=game.GameID, game_code=game.GameCode)
    except Exception as e:
        db.rollback()
        return jsonify(error="join_failed", detail=str(e)), 400
    finally:
        db.close()

# --- Join random (any waiting public game with free slot) ---
@games_bp.post("/join_random")
def join_random():
    uid, err = _require_login()
    if err:
        return err
    db = _db()
    try:
        game = (
            db.query(Game)
              .filter_by(Status="waiting", IsPrivate=False)
              .filter(Game.CurrentPlayersCount < Game.MaxPlayers)
              .order_by(func.random())
              .first()
        )
        if not game:
            return jsonify(error="no_games_available"), 404

        if not db.query(PlayerGame).filter_by(UserID=uid, GameID=game.GameID).first():
            db.add(PlayerGame(UserID=uid, GameID=game.GameID))
            game.CurrentPlayersCount += 1

        db.commit()
        return jsonify(ok=True, game_id=game.GameID, game_code=game.GameCode)
    except Exception as e:
        db.rollback()
        return jsonify(error="join_random_failed", detail=str(e)), 400
    finally:
        db.close()

# --- Lobby: list players (polling) ---
@games_bp.get("/<int:game_id>/lobby")
def lobby(game_id: int):
    uid, err = _require_login()
    if err:
        return err
    db = _db()
    try:
        game = db.query(Game).get(game_id)
        if not game:
            return jsonify(error="game_not_found"), 404
        # anyone who joined can see lobby
        rows = (
            db.query(User.Username)
              .join(PlayerGame, PlayerGame.UserID == User.UserID)
              .filter(PlayerGame.GameID == game_id)
              .all()
        )
        return jsonify(
            ok=True,
            status=game.Status,
            game_code=game.GameCode,
            players=[r[0] for r in rows],
            max_players=game.MaxPlayers
        )
    finally:
        db.close()

# --- Start game (creator only) + create Round + word set, then return room_url ---
@games_bp.post("/<int:game_id>/start")
def start_game(game_id: int):
    uid, err = _require_login()
    if err:
        return err

    db = _db()
    try:
        game = db.query(Game).get(game_id)
        if not game:
            return jsonify(error="game_not_found"), 404
        if game.CreatorID != uid:
            return jsonify(error="not_creator"), 403
        if game.Status != "waiting":
            return jsonify(error="bad_status"), 400

        # Word set
        wl = WordLoader()
        target = wl.generate_target_word()
        if isinstance(target, (list, tuple)) and target:
            target = target[0]
        target = str(target or "")

        forbidden_list = wl.generate_forbidden_list(target) or []
        if not isinstance(forbidden_list, (list, tuple)):
            forbidden_list = [str(forbidden_list)]
        forbidden_list = list(forbidden_list)

        round_rec = Round(
            GameID=game.GameID,
            RoundNumber=1,
            RoundWinnerID=None,            # now nullable ✔
            TargetWord=target,
            Description=None,              # no description yet
            ForbiddenWords=forbidden_list, # JSON column expects a Python list
            Hints=[],
            StartTime=None,                # set when description is accepted
            EndTime=None,
            MaxRoundTime=game.settings.RoundTimeSeconds if game.settings else 180,
            Status="waiting_description",  # clearer initial state
        )
        db.add(round_rec)

        game.Status = "active"
        game.StartedAt = dt.datetime.utcnow()
        db.commit()

        return jsonify(ok=True, room_url=f"/room/{game.GameID}")
    except Exception as e:
        db.rollback()
        import traceback; traceback.print_exc()
        return jsonify(error="start_failed", detail=str(e)), 400
    finally:
        db.close()

# --- My active / past games for right panel ---

@games_bp.get("/my_active")
def my_active():
    uid, err = _require_login()
    if err:
        return err

    db = _db()
    try:
        games = (
            db.query(Game)
              .join(PlayerGame, PlayerGame.GameID == Game.GameID)
              .filter(PlayerGame.UserID == uid)
              .filter(Game.Status.in_(["waiting", "active"]))
              .order_by(Game.CreatedAt.desc())
              .all()
        )

        out = []
        for g in games:
            total_rounds = int(getattr(g, "TotalRounds", 0) or 0)

            # currentRound = completed_count + 1 (but never exceed total_rounds if known)
            completed_count = (
                db.query(func.count(Round.RoundID))
                  .filter(Round.GameID == g.GameID, Round.Status == "completed")
                  .scalar()
            ) or 0

            # Start from 1 even if nothing completed yet
            current_round = completed_count + 1
            if total_rounds > 0:
                current_round = min(current_round, total_rounds)

            out.append({
                "id": g.GameID,
                "code": g.GameCode,
                "players": int(getattr(g, "CurrentPlayersCount", 0) or 0),
                "max": getattr(g, "MaxPlayers", None),
                "createdAt": g.CreatedAt.isoformat() + "Z" if getattr(g, "CreatedAt", None) else None,
                "startedAt": g.StartedAt.isoformat() + "Z" if getattr(g, "StartedAt", None) else None,
                "status": g.Status,
                "totalRounds": total_rounds or None,   # keep None if unknown
                "currentRound": int(max(1, current_round)),
            })

        return jsonify(out)
    finally:
        db.close()


@games_bp.get("/my_past")
def my_past_games():
    uid = session.get("user_id")
    if not uid:
        return jsonify(error="not_logged_in"), 401

    db = _db()
    try:
        q = (
            db.query(Game)
              .join(PlayerGame, PlayerGame.GameID == Game.GameID)
              .filter(PlayerGame.UserID == uid, Game.Status == "completed")
              .order_by(Game.EndedAt.desc().nullslast())
        )

        items = []
        for g in q.all():
            players = (
                db.query(User.Username)
                  .join(PlayerGame, PlayerGame.UserID == User.UserID)
                  .filter(PlayerGame.GameID == g.GameID)
                  .all()
            )
            players = [p[0] for p in players]
            duration_sec = None
            if g.StartedAt and g.EndedAt:
                duration_sec = int((g.EndedAt - g.StartedAt).total_seconds())

            winner = "None"
            if g.WinnerID:
                winner = db.query(User.Username).filter(User.UserID == g.WinnerID).scalar()

            items.append({
                "game_id": g.GameID,
                "game_code": g.GameCode,
                "ended_at": g.EndedAt.isoformat() + "Z" if g.EndedAt else None,
                "started_at": g.StartedAt.isoformat() + "Z" if g.StartedAt else None,
                "total_rounds": g.TotalRounds,
                "players_count": len(players),
                "players": players,
                "duration_sec": duration_sec,
                "winner": winner
            })

        return jsonify(ok=True, games=items)
    finally:
        db.close()
