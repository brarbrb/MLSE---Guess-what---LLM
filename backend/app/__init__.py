from flask import Flask
from .routes.users import users_bp
from .routes.games import games_bp
from .routes.auth import auth_bp           # NEW
from .routes.pages import pages_bp         # NEW
from .errors import register_error_handlers as _errors

def register_blueprints(app: Flask) -> None:
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(games_bp, url_prefix="/api/games")
    app.register_blueprint(auth_bp)        # no prefix (serves /, /login, /signup)
    app.register_blueprint(pages_bp)       # serves /menu etc.

def register_error_handlers(app: Flask) -> None:
    _errors(app)
