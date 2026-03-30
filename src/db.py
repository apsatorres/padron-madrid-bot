"""SQLite storage for per-user check configurations."""

import json
import sqlite3
from pathlib import Path

from .config import logger

DB_PATH = Path(__file__).resolve().parent.parent / "user_checks.db"

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL,
    category TEXT NOT NULL,
    procedure TEXT NOT NULL,
    preferred_offices TEXT DEFAULT '[]',
    active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def _connect():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _connect() as conn:
        conn.execute(_CREATE_TABLE)
        conn.commit()
    logger.info(f"Database initialised at {DB_PATH}")


def add_check(chat_id, category, procedure, preferred_offices=None):
    offices_json = json.dumps(preferred_offices or [])
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO checks (chat_id, category, procedure, preferred_offices) "
            "VALUES (?, ?, ?, ?)",
            (str(chat_id), category, procedure, offices_json),
        )
        conn.commit()
        return cur.lastrowid


def get_checks(chat_id):
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM checks WHERE chat_id = ? ORDER BY id", (str(chat_id),)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_all_active_checks():
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM checks WHERE active = 1 ORDER BY chat_id, id"
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def remove_check(chat_id, check_id):
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM checks WHERE id = ? AND chat_id = ?",
            (check_id, str(chat_id)),
        )
        conn.commit()
        return cur.rowcount > 0


def update_offices(chat_id, check_id, preferred_offices):
    offices_json = json.dumps(preferred_offices)
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE checks SET preferred_offices = ? WHERE id = ? AND chat_id = ?",
            (offices_json, check_id, str(chat_id)),
        )
        conn.commit()
        return cur.rowcount > 0


def set_active(chat_id, check_id, active):
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE checks SET active = ? WHERE id = ? AND chat_id = ?",
            (1 if active else 0, check_id, str(chat_id)),
        )
        conn.commit()
        return cur.rowcount > 0


def _row_to_dict(row):
    d = dict(row)
    d["preferred_offices"] = json.loads(d.get("preferred_offices") or "[]")
    return d
