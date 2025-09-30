from flask import Flask
from .routes.users import users_bp
from .routes.games import games_bp
from .errors import register_error_handlers as _errors

def register_blueprints(app: Flask) -> None:
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(games_bp, url_prefix="/api/games")

def register_error_handlers(app: Flask) -> None:
    _errors(app)
