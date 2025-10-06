import os

DB_URL = os.getenv("DB_URL", f"sqlite:///{os.getenv('SQLITE_PATH', '/app/data/app.db')}")
SQL_ECHO = os.getenv("SQL_ECHO", "").lower() in ("1","true","yes")
