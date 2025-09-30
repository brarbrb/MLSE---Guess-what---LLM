# backend/main.py
from flask import Flask, render_template, send_from_directory, jsonify, request
from pathlib import Path

# If you already have DB import/blueprints, keep them:
from .database.db import engine, Base
from .database import models
from .app import register_blueprints, register_error_handlers

# Compute absolute paths to the frontend folders
ROOT = Path(__file__).resolve().parents[1]       # repo root (.. from /backend)
FRONTEND_STATIC = ROOT / "frontend" / "static"   # css/js/images live here
FRONTEND_TEMPLATES = ROOT / "frontend" / "templates"  # index.html lives here

def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder=str(FRONTEND_STATIC),         # where /static/* will be served from
        template_folder=str(FRONTEND_TEMPLATES),    # where render_template looks
    )
    app.secret_key = "change-me"

    # ---- DB tables (optional if you have models) ----
    with app.app_context():
        Base.metadata.create_all(bind=engine)

    # ---- API blueprints (your JSON endpoints live under /api/...) ----
    register_blueprints(app)            # this should register /api/... routes
    register_error_handlers(app)

    # ---- HEALTH check (handy) ----
    @app.route("/api/health")
    def health():
        return jsonify(ok=True)

    # ---- Optional: direct file serving (rarely needed) ----
    # Example: /images/logo.png => /frontend/static/images/logo.png
    @app.route("/images/<path:filename>")
    def images(filename):
        return send_from_directory(FRONTEND_STATIC / "images", filename)

    # ---- SPA routes ----
    # 1) Root renders index.html
    @app.route("/")
    def index():
        # This will look in FRONTEND_TEMPLATES for index.html
        return render_template("index.html")

    # 2) Catch-all: if path doesn't start with 'api', serve the SPA
    #    so client-side routing (React/Router) works on refresh.
    @app.route("/<path:path>")
    def spa_fallback(path):
        # If someone tries to access /api/... but no route exists, return 404
        if path.startswith("api"):
            return jsonify(error="not_found"), 404
        # Otherwise send index.html so the frontend router can take over
        return render_template("index.html")

    return app

if __name__ == "__main__":
    create_app().run(debug=True)
