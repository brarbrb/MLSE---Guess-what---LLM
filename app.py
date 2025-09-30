# backend/app.py
from pathlib import Path
from flask import Flask, render_template

# Resolve absolute paths to the frontend assets
ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "frontend" / "templates"
STATIC = ROOT / "frontend" / "static"

app = Flask(
    __name__,
    template_folder=str(TEMPLATES),
    static_folder=str(STATIC),   # served automatically at /static/*
    static_url_path="/static",
)

# --- SPA entry points (React Router) ---
@app.route("/")
@app.route("/rooms/<pid>")
def spa_entry(pid=None):
    # Always deliver the same shell; React takes it from here.
    return render_template("index.html")

# Catch-all for any other client-side routes (e.g., /rooms/123/edit)
@app.route("/<path:subpath>")
def spa_fallback(subpath):
    # Let Flask handle real static files; only fallback for app routes.
    # Flask won't call this for /static/* because static_folder serves those.
    return render_template("index.html")


if __name__ == "__main__":
    # Run:  FLASK_APP=backend/app.py flask run --port 8000
    # or:   python backend/app.py
    app.run(host="127.0.0.1", port=8000, debug=True)
