from flask import Flask
from .routes.users import users_bp
from .routes.games import games_bp
from .routes.auth import auth_bp           
from .routes.pages import pages_bp         
from .routes.room_api import room_bp
from .routes.profile import profile_bp

from .errors import register_error_handlers as _errors

def register_blueprints(app: Flask) -> None:
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(games_bp, url_prefix="/api/games")
    app.register_blueprint(auth_bp)        # no prefix (serves /, /login, /signup)
    app.register_blueprint(pages_bp)       # serves /menu etc.
    app.register_blueprint(room_bp)
    app.register_blueprint(profile_bp)  # no prefix (API path is already /api/profile/...)


def register_error_handlers(app: Flask) -> None:
    _errors(app)
