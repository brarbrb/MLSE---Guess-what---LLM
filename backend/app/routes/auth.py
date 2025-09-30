# backend/app/routes/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from ...database.db import SessionLocal
from ...database.models import User

auth_bp = Blueprint("auth", __name__)

def _get_db():
    return SessionLocal()

@auth_bp.get("/landing")
@auth_bp.get("/")
def landing():
    # Landing with logo + buttons
    return render_template("landing.html")

@auth_bp.get("/signup")
def signup_get():
    return render_template("signup.html")

@auth_bp.post("/signup")
def signup_post():
    username = (request.form.get("username") or "").strip()
    email    = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    if not username or not email or not password:
        flash("Please fill all fields.", "error")
        return redirect(url_for("auth.signup_get"))

    db = _get_db()
    try:
        if db.query(User).filter((User.Username == username) | (User.Email == email)).first():
            flash("Username or email already exists.", "error")
            return redirect(url_for("auth.signup_get"))

        user = User(
            Username=username,
            Email=email,
            PasswordHash=generate_password_hash(password)
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Auto-login after signup
        session["user_id"] = user.UserID
        session["username"] = user.Username
        return redirect(url_for("pages.menu"))
    except Exception as e:
        db.rollback()
        flash(f"Sign up failed: {e}", "error")
        return redirect(url_for("auth.signup_get"))
    finally:
        db.close()

@auth_bp.get("/login")
def login_get():
    return render_template("login.html")

@auth_bp.post("/login")
def login_post():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""

    if not username or not password:
        flash("Please enter username and password.", "error")
        return redirect(url_for("auth.login_get"))

    db = _get_db()
    try:
        user = db.query(User).filter(User.Username == username).first()
        if not user or not check_password_hash(user.PasswordHash, password):
            # RED message on wrong creds
            flash("Wrong username or password.", "error")
            return redirect(url_for("auth.login_get"))

        session["user_id"] = user.UserID
        session["username"] = user.Username
        return redirect(url_for("pages.menu"))
    finally:
        db.close()

@auth_bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.landing"))
