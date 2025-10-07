import os
import sys
from pathlib import Path
import pytest

os.environ.setdefault("TESTING", "1")
os.environ.setdefault("FLASK_DEBUG", "0")
os.environ.setdefault("SQL_ECHO", "0")
os.environ.setdefault("DB_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("AI_BASE_URL", "http://localhost:9001")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))



from backend.main import create_app
from backend.database.db import SessionLocal, Base, engine
import uuid
from backend.database.models import User

@pytest.fixture(scope="session")
def app():
    app = create_app()
    app.config.update(TESTING=True)
    # DB tables are created by create_app(), but for safety ensure 
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


@pytest.fixture(autouse=True)
def _clean_db_between_tests():
    """Hard-reset the schema before each test to avoid cross-test leakage."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def login_session(client, db_session):
    """
    Create a user and return a context manager that logs them in by setting session values.
    Uses a unique username to avoid 409 conflicts across tests.
    """
    uname = f"testuser_{uuid.uuid4().hex[:8]}"
    payload = {"username": uname, "email": f"{uname}@t.com", "password_hash": "hunter2"}

    r = client.post('/api/users', json=payload)

    if r.status_code in (200, 201):
        user_id = r.get_json().get("UserID")
    elif r.status_code == 409:
        # If some parallel/previous test created it, fetch the id directly from DB
        u = db_session.query(User).filter_by(Username=uname).first()
        assert u is not None, "Expected to find existing user after 409"
        user_id = u.UserID
    else:
        raise AssertionError(f"Unexpected status from /api/users: {r.status_code} {r.data}")

    class _LoginCtx:
        def __enter__(self):
            with client.session_transaction() as sess:
                sess["user_id"] = user_id
                sess["username"] = uname
            return user_id
        def __exit__(self, exc_type, exc, tb):
            with client.session_transaction() as sess:
                sess.clear()
    return _LoginCtx()