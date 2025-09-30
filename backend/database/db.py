# backend/database/db.py
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DB_URL = "sqlite:///guesswhat.db"   # file in project root; adjust as you like

engine = create_engine(
    DB_URL,
    echo=False,
    future=True
)

# Enforce foreign keys in SQLite:
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

class Base(DeclarativeBase):
    pass
