from flask import Blueprint, render_template, session, redirect, url_for, abort
from ...database.db import SessionLocal
from ...database.models import PlayerGame, Game

pages_bp = Blueprint("pages", __name__)

def login_required(view):
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login_get"))
        return view(*args, **kwargs)
    wrapper.__name__ = view.__name__
    return wrapper

@pages_bp.get("/menu")
@login_required
def menu():
    return render_template("menu.html")

@pages_bp.get("/room/<int:game_id>")
@login_required
def room(game_id: int):
    uid = session["user_id"]
    db = SessionLocal()
    try:
        game = db.query(Game).get(game_id)
        if not game:
            abort(404)
        in_game = db.query(PlayerGame).filter_by(UserID=uid, GameID=game_id).first()
        if not in_game:
            return redirect(url_for("pages.menu"))
        return render_template("room.html")
    finally:
        db.close()