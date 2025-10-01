import os, sqlite3, time

DB_PATH = "guesswhat.db"   # put the exact relative/absolute path you use everywhere

def abs_db_path():
    return os.path.abspath(DB_PATH)

def show_tables_and_counts(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name;
    """)
    tables = [r[0] for r in cur.fetchall()]
    print("\nTables and row counts BEFORE wipe:")
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM {t};")
        cnt = cur.fetchone()[0]
        print(f" - {t}: {cnt}")
    return tables

def wipe_all(conn):
    cur = conn.cursor()
    # Turn OFF FKs to avoid constraint errors while bulk-deleting
    cur.execute("PRAGMA foreign_keys = OFF;")

    tables = show_tables_and_counts(conn)

    # Delete rows from every user table
    for t in tables:
        cur.execute(f"DELETE FROM {t};")

    # Reset AUTOINCREMENT counters if table exists
    cur.execute("SELECT name FROM sqlite_master WHERE name='sqlite_sequence';")
    if cur.fetchone():
        cur.execute("DELETE FROM sqlite_sequence;")

    conn.commit()

def vacuum():
    # VACUUM must be outside a transaction
    with sqlite3.connect(DB_PATH) as c2:
        c2.execute("VACUUM;")

def verify_after():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name;
        """)
        tables = [r[0] for r in cur.fetchall()]
        print("\nTables and row counts AFTER wipe:")
        for t in tables:
            cur.execute(f"SELECT COUNT(*) FROM {t};")
            cnt = cur.fetchone()[0]
            print(f" - {t}: {cnt}")

if __name__ == "__main__":
    print("Using DB:", abs_db_path())
    if not os.path.exists(DB_PATH):
        raise SystemExit("!! DB file not found at this path.")

    with sqlite3.connect(DB_PATH) as conn:
        wipe_all(conn)

    vacuum()
    verify_after()

    print("\nDone at", time.strftime("%Y-%m-%d %H:%M:%S"))
