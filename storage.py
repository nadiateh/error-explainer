import sqlite3
from contextlib import contextmanager
from datetime import datetime

import config

@contextmanager
def open_db():
    connection = sqlite3.connect(config.DB_PATH)
    connection.row_factory = sqlite3.Row
    
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db():
    with open_db() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS errors (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at  TEXT NOT NULL,
                error_text  TEXT NOT NULL,
                explanation TEXT NOT NULL
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS followups (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                error_id   INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                question   TEXT NOT NULL,
                answer     TEXT NOT NULL
            )
        """)

def save_error(error_text, explanation):
    created_at = datetime.now().isoformat(timespec="seconds")
    with open_db() as connection:
        cursor = connection.execute(
            "INSERT INTO errors (created_at, error_text, explanation) VALUES (?, ?, ?)",
            (created_at, error_text, explanation),
        )
        return cursor.lastrowid

def get_recent_errors(limit=10):
    with open_db() as connection:
        rows = connection.execute(
            "SELECT id, created_at, error_text FROM errors ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]

def get_error(error_id):
    with open_db() as connection:
        row = connection.execute(
            "SELECT * FROM errors WHERE id = ?",
            (error_id,),
        ).fetchone()
    return dict(row) if row else None

def search_errors(search_text, limit=20):
    pattern = f"%{search_text}%"
    with open_db() as connection:
        rows = connection.execute(
            "SELECT id, created_at, error_text FROM errors "
            "WHERE error_text LIKE ? OR explanation LIKE ? "
            "ORDER BY id DESC LIMIT ?",
            (pattern, pattern, limit),
        ).fetchall()
    return [dict(row) for row in rows]

def delete_error(error_id):
    with open_db() as connection:
        connection.execute("DELETE FROM followups WHERE error_id = ?", (error_id,))
        connection.execute("DELETE FROM errors WHERE id = ?", (error_id,))

def save_followup(error_id, question, answer):
    created_at = datetime.now().isoformat(timespec="seconds")
    with open_db() as connection:
        connection.execute(
            "INSERT INTO followups (error_id, created_at, question, answer) VALUES (?, ?, ?, ?)",
            (error_id, created_at, question, answer),
        )


def get_followups(error_id):
    with open_db() as connection:
        rows = connection.execute(
            "SELECT question, answer FROM followups WHERE error_id = ? ORDER BY id",
            (error_id,),
        ).fetchall()
    return [dict(row) for row in rows]

def count_errors():
    with open_db() as connection:
        row = connection.execute("SELECT COUNT(*) FROM errors").fetchone()
    return row[0]


if __name__ == "__main__":
    init_db()
    new_id = save_error("TestError: this is a test", "This is a test explanation.")
    print("Saved test entry with id", new_id)

    print("\nMost recent entries:")
    for entry in get_recent_errors():
        print(entry["id"], entry["created_at"], entry["error_text"][:50])

    print("\nFull entry", new_id, ":")
    print(get_error(new_id))