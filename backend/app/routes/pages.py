from flask import Blueprint, render_template, session, redirect, url_for

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
