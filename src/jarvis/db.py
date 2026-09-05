"""Structured store: goals, tasks, routine blocks. Plain SQLite — this is
operational data with real fields, the kind Mem0's fuzzy vector search is the
wrong tool for ("what's due Thursday" needs an exact answer). Single-user, so
no ownership/tenant columns.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "jarvis.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    horizon TEXT NOT NULL,
    priority_notes TEXT,
    archived INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    due_date TEXT,
    done INTEGER NOT NULL DEFAULT 0,
    completed_at TEXT,
    outcome TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS routine_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day_of_week TEXT NOT NULL,
    start_time TEXT NOT NULL,
    activity TEXT NOT NULL,
    fixed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        # Migrate existing DBs created before these columns existed.
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(tasks)")}
        if "completed_at" not in existing:
            conn.execute("ALTER TABLE tasks ADD COLUMN completed_at TEXT")
        if "outcome" not in existing:
            conn.execute("ALTER TABLE tasks ADD COLUMN outcome TEXT")


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict]:
    return [dict(row) for row in rows]


def log_task_outcome(task_id: int, outcome: str) -> None:
    """Set a task's outcome directly — called from a Telegram button tap, not
    the LLM. Logging how something went is a fixed action, not a judgment
    call, so it doesn't need to go through the agent loop."""
    with get_connection() as conn:
        conn.execute("UPDATE tasks SET outcome = ? WHERE id = ?", (outcome, task_id))


def get_task(task_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row) if row else None
