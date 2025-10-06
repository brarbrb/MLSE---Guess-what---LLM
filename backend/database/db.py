# from sqlalchemy import create_engine, event
# from sqlalchemy.orm import sessionmaker, DeclarativeBase

# DB_URL = "sqlite:///guesswhat.db"   

# engine = create_engine(
#     DB_URL,
#     echo=False,
#     future=True
# )

# @event.listens_for(engine, "connect")
# def _set_sqlite_pragma(dbapi_conn, connection_record):
#     cursor = dbapi_conn.cursor()
#     cursor.execute("PRAGMA foreign_keys=ON")
#     cursor.close()

# SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# class Base(DeclarativeBase):
#     pass


# from sqlalchemy import create_engine, event
# from sqlalchemy.orm import sessionmaker, DeclarativeBase
# import os

# # ----- config from env with safe fallbacks -----
# DB_URL = os.getenv("DB_URL") or f"sqlite:///{os.getenv('SQLITE_PATH', '/app/data/app.db')}"
# SQL_ECHO = os.getenv("SQL_ECHO", "").lower() in ("1", "true", "yes")

# # ----- single engine (add check_same_thread only for sqlite) -----
# connect_args = {}
# if DB_URL.startswith("sqlite"):
#     connect_args["check_same_thread"] = False

# engine = create_engine(
#     DB_URL,
#     echo=SQL_ECHO,
#     future=True,
#     connect_args=connect_args,
# )

# # ----- enforce foreign keys in SQLite only -----
# @event.listens_for(engine, "connect")
# def _set_sqlite_pragma(dbapi_conn, connection_record):
#     # Only applies on sqlite connections
#     try:
#         if engine.url.get_backend_name() == "sqlite":
#             cursor = dbapi_conn.cursor()
#             cursor.execute("PRAGMA foreign_keys=ON")
#             cursor.close()
#     except Exception:
#         pass

# SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# class Base(DeclarativeBase):
#     pass


# backend/database/db.py
from __future__ import annotations
import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Project root: backend/database -> go up two levels
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Default DB location works locally; Docker can still override via env
default_sqlite = PROJECT_ROOT / "data" / "app.db"

# Use env if set; otherwise default
sqlite_path = Path(os.getenv("SQLITE_PATH", str(default_sqlite)))

# Ensure directory exists
sqlite_path.parent.mkdir(parents=True, exist_ok=True)

# Build a proper sqlite URL (Path takes care of Windows backslashes)
DB_URL = f"sqlite:///{sqlite_path.as_posix()}"

engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False},  # needed for SQLite + threads
    echo=False,
    future=True,
)

# Enforce foreign keys in SQLite
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

class Base(DeclarativeBase):
    pass
