from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from pdf2zh_next.const import DEFAULT_CONFIG_DIR


DEFAULT_DB_PATH = DEFAULT_CONFIG_DIR / "auth.db"


def _get_db_path() -> Path:
    custom = os.getenv("PDF2ZH_DB_PATH")
    if custom:
        path = Path(custom).expanduser()
    else:
        path = DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def init_db() -> None:
    path = _get_db_path()
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                display_name TEXT,
                api_token TEXT UNIQUE,
                retention_days INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                owner TEXT NOT NULL,
                filename TEXT NOT NULL,
                input_path TEXT NOT NULL,
                output_dir TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                retention_days INTEGER,
                progress REAL DEFAULT 0,
                message TEXT,
                result_json TEXT,
                events_json TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tasks_owner_created
            ON tasks (owner, created_at DESC)
            """
        )
        conn.commit()


@contextmanager
def get_connection() -> sqlite3.Connection:
    path = _get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


__all__ = ["init_db", "get_connection"]
