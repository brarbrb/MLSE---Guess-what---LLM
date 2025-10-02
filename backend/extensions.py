# backend/extensions.py
from flask_socketio import SocketIO

# CORS "*" is OK for local dev. Tighten later.
socketio = SocketIO(cors_allowed_origins="*")
