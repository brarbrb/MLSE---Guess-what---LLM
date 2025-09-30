import sqlite3

# --- Change this to the path of your database file ---
DB_PATH = "guesswhat.db"

def list_tables(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("\nTables in database:")
    for t in tables:
        print(" -", t[0])
    return [t[0] for t in tables]

def show_table_contents(conn, table, limit=10):
    cursor = conn.cursor()
    print(f"\nContents of table '{table}':")
    cursor.execute(f"SELECT * FROM {table} LIMIT {limit};")
    rows = cursor.fetchall()

    # Print column names
    col_names = [description[0] for description in cursor.description]
    print(" | ".join(col_names))
    print("-" * 40)

    for row in rows:
        print(row)

def main():
    conn = sqlite3.connect(DB_PATH)

    tables = list_tables(conn)
    for t in tables:
        show_table_contents(conn, t)

    conn.close()

if __name__ == "__main__":
    main()
