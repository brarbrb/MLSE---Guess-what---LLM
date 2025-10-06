from flask import Blueprint, request, jsonify, session
from ...database.db import SessionLocal
from ...database.models import Game, PlayerGame, Round, Guess, User,  GameSettings, ChatMessage
from ...extensions import socketio
from sqlalchemy import func

import datetime as dt
import re
import json

room_bp = Blueprint("room_api", __name__)

import os, requests  
AI_BASE_URL = os.getenv("AI_BASE_URL", "http://ai:9001")

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

def _emit_ai(game_id, phase, **extra):
    _emit("round:ai_progress", {"phase": phase, **extra}, game_id)

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

        # tell clients (creator sees "Verifying…")
        _emit_ai(game_id, "validating_desc")   # <<< ADDED

        # Disallow target/forbidden words from appearing as whole words
        norm_desc = _normalize(text)
        norm_target = _normalize(rnd.TargetWord)
        if norm_target and re.search(rf"(?:^| ){re.escape(norm_target)}(?: |$)", norm_desc):
            _emit_ai(game_id, "desc_bad", reason=f'Used target word "{rnd.TargetWord}"')  # <<< ADDED
            return jsonify(error="forbidden_word_used", which=rnd.TargetWord), 400

        for w in (rnd.ForbiddenWords or []):
            nw = _normalize(w)
            if nw and re.search(rf"(?:^| ){re.escape(nw)}(?: |$)", norm_desc):
                _emit_ai(game_id, "desc_bad", reason=f'Used forbidden word "{w}"')  # <<< ADDED
                return jsonify(error="forbidden_word_used", which=w), 400

        # Optional AI verification
        try:
            payload = {
                "targetWord": rnd.TargetWord,
                "forbiddenWords": list(rnd.ForbiddenWords or []),
                "description": text,
            }
            chk = requests.post(f"{AI_BASE_URL}/check_description", json=payload, timeout=20)
            chk.raise_for_status()
            verdict = chk.json()
            if not verdict.get("ok", False):
                _emit_ai(  # <<< ADDED
                    game_id,
                    "desc_bad",
                    reason=verdict.get("reason") or "Description violates constraints.",
                )
                return jsonify(
                    error="forbidden_word_used_ai",
                    which=verdict.get("violated", []),
                    reason=verdict.get("reason"),
                ), 400
        except Exception:
            # Degraded AI => proceed (keep verifying UI until we accept)
            pass

        # Accept description
        rnd.Description = text
        if not rnd.StartTime:
            rnd.StartTime = dt.datetime.utcnow()
        rnd.Status = "active"
        db.commit()

        # tell clients: accepted (creator UI can close if you listen to desc_ok)
        _emit_ai(game_id, "desc_ok")  # <<< ADDED

        # existing broadcast that drives everyone to "active" + closes waiting modal
        _emit("round:description", {
            "description": rnd.Description,
            "startedAt": rnd.StartTime.isoformat() + "Z"
        }, game_id)

        return jsonify(ok=True, message="Description accepted", startedAt=rnd.StartTime.isoformat() + "Z")
    except Exception as e:
        db.rollback()
        # if something blows up after we showed "validating", let UI recover:
        _emit_ai(game_id, "desc_bad", reason="Server error while saving description.")  # <<< ADDED (best-effort)
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
        guess_raw = (data.get("guess") or data.get("text") or "").strip()
        if not guess_raw:
            return jsonify(error="empty_guess"), 400

        # normalize & compare
        target_n  = _normalize(rnd.TargetWord)
        guess_n   = _normalize(guess_raw)
        correct   = (guess_n == target_n)

        # timings
        now = dt.datetime.utcnow()
        elapsed_sec = max(0.0, (now - (rnd.StartTime or now)).total_seconds())
        elapsed_ms  = int(elapsed_sec * 1000)

        # persist Guess
        g = Guess(
            GameID=game_id,
            RoundID=rnd.RoundID,
            GuesserID=uid,
            GuessText=guess_raw,
            GuessTime=now,
            ResponseTimeSeconds=elapsed_sec,
            PointsAwarded=0,
            IsCorrect=False
        )
        db.add(g)

        # also persist ChatMessage (best-effort)
        try:
            msg = ChatMessage(
                GameID=game_id,
                RoundID=rnd.RoundID,
                SenderID=uid,
                MessageText=guess_raw,
                MessageType="guess",
                Timestamp=now,
                IsVisible=1,
            )
            db.add(msg)
        except Exception:
            pass  # okay if ChatMessage model differs or is absent

        # emit chat to clients so UI shows it immediately
        # emit chat to clients so UI shows it immediately (match frontend Room JS)
        sender_name = db.query(User.Username).filter(User.UserID == uid).scalar()
        _emit("chat:new", {
            "user": sender_name,                 # <-- KEY FIX
            "text": guess_raw                    # <-- frontend uses msg.text
        }, game.GameID)

        # --- PlayerGame stats updates ---
        pg = db.query(PlayerGame).filter_by(GameID=game.GameID, UserID=uid).one()
        pg.TotalGuesses = int(pg.TotalGuesses or 0) + 1

        if correct and rnd.Status != "completed" and rnd.RoundWinnerID is None:
            # award points (from settings, default 100)
            settings = db.query(GameSettings).filter(GameSettings.GameID == game.GameID).first()
            award = int(getattr(settings, "PointsCorrectGuess", 100) or 100)

            # finalize round
            rnd.RoundWinnerID = uid
            rnd.EndTime = now
            rnd.Status = "completed"
            g.PointsAwarded = award
            g.IsCorrect = True

            # correct-guess stats
            prev_n  = int(pg.TotalCorrectGuesses or 0)
            new_n   = prev_n + 1
            prevavg = float(pg.AverageGuessTime or 0.0)
            newavg  = ((prevavg * prev_n) + elapsed_sec) / new_n
            pg.TotalCorrectGuesses = new_n
            pg.AverageGuessTime    = newavg
            if pg.BestGuessTime is None:
                pg.BestGuessTime = elapsed_sec
            else:
                pg.BestGuessTime = min(float(pg.BestGuessTime), elapsed_sec)
            pg.PlayerFinalScore = int(pg.PlayerFinalScore or 0) + award

            # ----- CURRENT LEADER (leaderboard top), NOT turn owner -----
            # find previous top before we recompute (to update TimesAsLeader if leadership changes)
                        # ----- CURRENT LEADER (highest score so far), NOT turn owner -----
            prev_top = (
                db.query(PlayerGame.UserID, PlayerGame.PlayerFinalScore)
                  .filter(PlayerGame.GameID == game.GameID)
                  .order_by(PlayerGame.PlayerFinalScore.desc(), PlayerGame.UserID.asc())
                  .first()
            )
            prev_top_user = prev_top[0] if prev_top else None

            # recompute top after this award
            new_top = (
                db.query(PlayerGame.UserID, PlayerGame.PlayerFinalScore)
                  .filter(PlayerGame.GameID == game.GameID)
                  .order_by(PlayerGame.PlayerFinalScore.desc(), PlayerGame.UserID.asc())
                  .first()
            )
            if new_top:
                game.CurrentLeaderID = int(new_top[0])

            if new_top and int(new_top[0]) == uid and prev_top_user != uid:
                pg.TimesAsLeader = int(pg.TimesAsLeader or 0) + 1

            # Advance currentRound = min(rnd.RoundNumber + 1, TotalRounds)
            if game.TotalRounds:
                game.CurrentRound = min((rnd.RoundNumber or 1) + 1, game.TotalRounds)
            else:
                game.CurrentRound = (rnd.RoundNumber or 1) + 1

            # ---- Decide last round WITHOUT counting ----
            is_last_round = bool(game.TotalRounds) and (rnd.RoundNumber >= game.TotalRounds)

            if is_last_round:
                # finalize game (pick winner by highest score)
                final_top = (
                    db.query(PlayerGame.UserID, PlayerGame.PlayerFinalScore)
                      .filter(PlayerGame.GameID == game.GameID)
                      .order_by(PlayerGame.PlayerFinalScore.desc(), PlayerGame.UserID.asc())
                      .first()
                )
                if final_top:
                    game.WinnerID = int(final_top[0])
                    for pg_row in db.query(PlayerGame).filter(PlayerGame.GameID == game.GameID).all():
                        pg_row.HasWon = (pg_row.UserID == game.WinnerID)

                game.Status = "completed"
                game.EndedAt = now
                db.commit()
            else:
                # create next round; turn stays with creator
                next_rn = (rnd.RoundNumber or 1) + 1

                try:
                    ai_resp = requests.post(f"{AI_BASE_URL}/gen_words", json={}, timeout=30)
                    ai_resp.raise_for_status()
                    ai_data = ai_resp.json()
                    target_word = str(ai_data.get("targetWord", "")).strip().lower()
                    forbidden_list = list(ai_data.get("forbiddenWords") or [])
                    if not target_word or not forbidden_list:
                        raise ValueError("AI returned incomplete words")
                except Exception:
                    # safe fallback
                    target_word = "tree"
                    forbidden_list = ["leaf", "wood", "forest"]

                new_round = Round(
                    GameID=game.GameID,
                    RoundNumber=next_rn,
                    RoundWinnerID=None,
                    TargetWord=target_word,
                    Description=None,             # player will fill in
                    ForbiddenWords=forbidden_list,
                    Hints=[],
                    StartTime=None,
                    EndTime=None,
                    MaxRoundTime=rnd.MaxRoundTime,
                    Status="waiting_description",
                )
                db.add(new_round)
                game.Status = "active"
                db.commit()

            # notify clients of round win
            _emit("round:won", {
                "winner": sender_name,
                "word": rnd.TargetWord,
                "elapsedMs": elapsed_ms,
                "roundNumber": rnd.RoundNumber,
                "totalRounds": game.TotalRounds,
                "gameCompleted": (game.Status == "completed")
            }, game.GameID)

            return jsonify(
                correct=True,
                message="🎉 Correct! You won!",
                winner=sender_name,
                elapsedMs=elapsed_ms,
                word=rnd.TargetWord,
                roundNumber=rnd.RoundNumber,
                totalRounds=game.TotalRounds,
                gameCompleted=(game.Status == "completed")
            )

        else:
            # wrong guess: just commit persisted Guess and stats
            db.commit()
            return jsonify(correct=False, message="Nope, try again")
    except Exception as e:
        db.rollback()
        return jsonify(error="guess_failed", detail=str(e)), 400
    finally:
        db.close()


@room_bp.get("/api/room/<int:game_id>/chat")
def get_chat_history(game_id: int):
    db = _db()
    try:
        uid, err = _require_member(db, game_id)
        if err:
            return err

        # query params
        limit = max(1, min(int(request.args.get("limit", 200) or 200), 500))
        since_iso = request.args.get("since")
        only_current_round = (request.args.get("round") == "current")

        since_dt = None
        if since_iso:
            try:
                since_dt = dt.datetime.fromisoformat(since_iso.replace("Z", "+00:00"))
            except Exception:
                since_dt = None

        # If round=current, resolve the latest round number
        round_filter = None
        if only_current_round:
            latest = (
                db.query(Round)
                  .filter(Round.GameID == game_id)
                  .order_by(Round.RoundNumber.desc())
                  .first()
            )
            if latest:
                round_filter = latest.RoundID

        # Do we have ChatMessage rows at all for this game?
        has_cm = (
            db.query(ChatMessage.MessageID)
              .filter(ChatMessage.GameID == game_id)
              .first()
            is not None
        )

        messages = []

        if has_cm:
            # Primary source = ChatMessage
            q = db.query(ChatMessage, User.Username)\
                  .join(User, User.UserID == ChatMessage.SenderID)\
                  .filter(ChatMessage.GameID == game_id)
            if round_filter:
                q = q.filter(ChatMessage.RoundID == round_filter)
            if since_dt:
                q = q.filter(ChatMessage.Timestamp > since_dt)
            q = q.order_by(ChatMessage.Timestamp.asc()).limit(limit)

            for cm, uname in q.all():
                messages.append({
                    "user": uname or "Unknown",
                    "text": cm.MessageText or "",
                    "ts": (cm.Timestamp.isoformat() + "Z") if cm.Timestamp else None,
                    "type": cm.MessageType or "chat"
                })
        else:
            # Fallback for legacy games = use Guess table
            q = db.query(Guess, User.Username)\
                  .join(User, User.UserID == Guess.GuesserID)\
                  .filter(Guess.GameID == game_id)
            if round_filter:
                q = q.filter(Guess.RoundID == round_filter)
            if since_dt:
                q = q.filter(Guess.GuessTime > since_dt)
            q = q.order_by(Guess.GuessTime.asc()).limit(limit)

            for g, uname in q.all():
                messages.append({
                    "user": uname or "Unknown",
                    "text": g.GuessText or "",
                    "ts": (g.GuessTime.isoformat() + "Z") if g.GuessTime else None,
                    "type": "guess"
                })

        return jsonify(ok=True, messages=messages)
    except Exception as e:
        return jsonify(ok=False, error="chat_history_failed", detail=str(e)), 400
    finally:
        db.close()