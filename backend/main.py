# backend/main.py
from flask import Flask, render_template, send_from_directory, jsonify, request, redirect, url_for, session
from pathlib import Path
from datetime import timedelta
from .database.db import engine, Base
from .database import models
from .app import register_blueprints, register_error_handlers

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_STATIC = ROOT / "frontend" / "static"
FRONTEND_TEMPLATES = ROOT / "frontend" / "templates"

def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder=str(FRONTEND_STATIC),
        # static_url_path="/static",                 # <- ensure /static works
        template_folder=str(FRONTEND_TEMPLATES),
    )
    app.secret_key = "change-me"

    with app.app_context():
        Base.metadata.create_all(bind=engine)

    register_blueprints(app)
    register_error_handlers(app)

    @app.get("/api/health")
    def health():
        return jsonify(ok=True)

    # Serve landing directly here (matches our auth.landing too; keep one of them)
    @app.get("/")
    def root():
        if session.get("user_id"):   # already logged in
            return redirect(url_for("pages.menu"))
        return render_template("landing.html")

    # Optional helper for images (you can delete if unused)
    @app.get("/images/<path:filename>")
    def images(filename):
        return send_from_directory(FRONTEND_STATIC / "images", filename)
    app.permanent_session_lifetime = timedelta(days=7)
    return app

if __name__ == "__main__":
    create_app().run(debug=True)
