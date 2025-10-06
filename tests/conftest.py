import os
import sys
from pathlib import Path
import pytest

# Ensure env is set BEFORE importing the app, because backend/database/db.py
# reads DB_URL at import time.
os.environ.setdefault("TESTING", "1")
os.environ.setdefault("FLASK_DEBUG", "0")
os.environ.setdefault("SQL_ECHO", "0")
# Ephemeral SQLite (pysqlite dialect); if your Python lacks pysqlite, fall back to file sqlite.
os.environ.setdefault("DB_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("AI_BASE_URL", "http://localhost:9001")

# Make sure we can import 'backend'
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import create_app
from backend.database.db import SessionLocal, Base, engine

@pytest.fixture(scope="session")
def app():
    app = create_app()
    app.config.update(TESTING=True)
    # DB tables are created by create_app(), but for safety ensure fresh metadata exists
    with app.app_context():
        Base.metadata.create_all(bind=engine)
    yield app

@pytest.fixture(scope="function")
def client(app):
    return app.test_client()

@pytest.fixture(scope="function")
def db_session():
    """New SQLAlchemy session per test function."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def login_session(client, db_session):
    """Create a user and return a context manager that logs them in by setting session values."""
    # Create user via API to keep behavior realistic
    r = client.post('/api/users', json={"username": "testuser", "email": "t@t", "password_hash": "x"})
    assert r.status_code in (200, 201), r.data
    user_id = r.get_json().get("UserID")
    assert user_id

    class _LoginCtx:
        def __enter__(self):
            # Bypass HTML login form: directly set session keys
            with client.session_transaction() as sess:
                sess["user_id"] = user_id
                sess["username"] = "testuser"
            return user_id
        def __exit__(self, exc_type, exc, tb):
            with client.session_transaction() as sess:
                sess.clear()
    return _LoginCtx()
