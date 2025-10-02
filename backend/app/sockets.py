# backend/app/sockets.py
from flask import session, request
from flask_socketio import join_room
from ..extensions import socketio

from .routes.room_api import _db, _require_member, _normalize
from ..database.models import Game, PlayerGame, Round, Guess, User
import datetime as dt

def _room(game_id: int) -> str:
    return f"game-{game_id}"

@socketio.on("room:join")
def on_room_join(data):
    game_id = int(data.get("game_id", 0)) if data else 0
    if not game_id:
        return
    db = _db()
    try:
        uid, err = _require_member(db, game_id)
        if err:
            socketio.emit("room:error", {"error": "not_in_game"}, to=request.sid)
            return
        join_room(_room(game_id))
        socketio.emit("room:joined", {"ok": True, "game_id": game_id}, to=request.sid)
    finally:
        db.close()

@socketio.on("chat:send")
def on_chat_send(data):
    """
    payload: { game_id: int, text: str }
    Broadcast chat line, and if it equals the target, mark winner & announce.
    """
    if not data:
        return
    txt = (data.get("text") or "").strip()
    game_id = int(data.get("game_id", 0)) if data.get("game_id") is not None else 0
    if not txt or not game_id:
        return

    db = _db()
    try:
        uid, err = _require_member(db, game_id)
        if err:
            socketio.emit("room:error", {"error": "not_in_game"}, to=request.sid)
            return

        game = db.query(Game).get(game_id)
        if not game:
            socketio.emit("room:error", {"error": "game_not_found"}, to=request.sid)
            return

        rnd = (
            db.query(Round)
            .filter_by(GameID=game_id)
            .order_by(Round.RoundNumber.desc())
            .first()
        )

        # Broadcast the chat message
        socketio.emit("chat:new", {
            "user": session.get("username", "anon"),
            "text": txt
        }, to=_room(game_id))

        # If round not ready, it's just chat
        if not rnd or not rnd.Description:
            return

        # Guess check
        guess  = _normalize(txt)
        target = _normalize(rnd.TargetWord)
        correct = (guess == target)

        now = dt.datetime.utcnow()
        # Persist guess (optional but you have a table)
        g = Guess(
            GameID=game_id,
            RoundID=rnd.RoundID,
            GuesserID=uid,
            GuessText=txt,
            ResponseTimeSeconds=((now - (rnd.StartTime or now)).total_seconds()),
            IsCorrect=bool(correct)
        )
        db.add(g)

        if correct and rnd.Status != "completed" and (rnd.RoundWinnerID is None):
            rnd.RoundWinnerID = uid
            rnd.EndTime = now
            rnd.Status = "completed"
            db.commit()

            winner_name = db.query(User.Username).filter(User.UserID == uid).scalar()
            socketio.emit("round:won", {
                "winner": winner_name,
                "word": rnd.TargetWord,
                "elapsedMs": int(((now - (rnd.StartTime or now)).total_seconds()) * 1000)
            }, to=_room(game_id))
        else:
            db.commit()
    finally:
        db.close()
