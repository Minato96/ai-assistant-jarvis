"""CRUD tools over the structured store, bound to the LLM for tool-calling.

These are fixed-path operations (add a task, mark it done, ...) — the LLM's
only job is to decide *when* to call one and with *what arguments*, not to
freeform describe what happened. Keeping that boundary is why this graph uses
LangGraph's tool-calling loop instead of one prompt that does everything.
"""
from __future__ import annotations

from langchain_core.tools import tool

from .db import get_connection, rows_to_dicts


@tool
def add_goal(name: str, horizon: str, priority_notes: str = "") -> dict:
    """Add a new goal. horizon is free text describing the timeframe, e.g.
    'this semester', 'before graduation', 'long-term'."""
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO goals (name, horizon, priority_notes) VALUES (?, ?, ?)",
            (name, horizon, priority_notes or None),
        )
        return {"id": cur.lastrowid, "name": name, "horizon": horizon}


@tool
def list_goals(include_archived: bool = False) -> list[dict]:
    """List goals. By default only active (non-archived) goals."""
    query = "SELECT * FROM goals"
    if not include_archived:
        query += " WHERE archived = 0"
    query += " ORDER BY created_at"
    with get_connection() as conn:
        return rows_to_dicts(conn.execute(query).fetchall())


@tool
def update_goal(
    goal_id: int,
    name: str = "",
    horizon: str = "",
    priority_notes: str = "",
    archived: bool | None = None,
) -> dict:
    """Update a goal. Leave a text field empty to keep it unchanged. Set
    archived=true to retire a goal without deleting its history."""
    fields, values = [], []
    if name:
        fields.append("name = ?")
        values.append(name)
    if horizon:
        fields.append("horizon = ?")
        values.append(horizon)
    if priority_notes:
        fields.append("priority_notes = ?")
        values.append(priority_notes)
    if archived is not None:
        fields.append("archived = ?")
        values.append(int(archived))
    if not fields:
        return {"updated": False, "reason": "no fields provided"}
    values.append(goal_id)
    with get_connection() as conn:
        conn.execute(f"UPDATE goals SET {', '.join(fields)} WHERE id = ?", values)
        return {"updated": True, "id": goal_id}


@tool
def delete_goal(goal_id: int) -> dict:
    """Permanently delete a goal. Prefer update_goal(archived=true) unless the
    user explicitly wants it gone."""
    with get_connection() as conn:
        conn.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
        return {"deleted": True, "id": goal_id}


@tool
def add_task(title: str, due_date: str = "") -> dict:
    """Add a task. due_date is an ISO date string (YYYY-MM-DD) if known."""
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (title, due_date) VALUES (?, ?)",
            (title, due_date or None),
        )
        return {"id": cur.lastrowid, "title": title, "due_date": due_date or None}


@tool
def list_tasks(include_done: bool = False) -> list[dict]:
    """List tasks. By default only tasks that aren't done yet, soonest due
    first (tasks with no due date last)."""
    query = "SELECT * FROM tasks"
    if not include_done:
        query += " WHERE done = 0"
    query += " ORDER BY due_date IS NULL, due_date"
    with get_connection() as conn:
        return rows_to_dicts(conn.execute(query).fetchall())


@tool
def update_task(
    task_id: int, title: str = "", due_date: str = "", done: bool | None = None
) -> dict:
    """Update a task. Leave a text field empty to keep it unchanged. Set
    done=true to mark it complete."""
    fields, values = [], []
    if title:
        fields.append("title = ?")
        values.append(title)
    if due_date:
        fields.append("due_date = ?")
        values.append(due_date)
    if done is not None:
        fields.append("done = ?")
        values.append(int(done))
    if not fields:
        return {"updated": False, "reason": "no fields provided"}
    values.append(task_id)
    with get_connection() as conn:
        conn.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?", values)
        return {"updated": True, "id": task_id}


@tool
def delete_task(task_id: int) -> dict:
    """Permanently delete a task."""
    with get_connection() as conn:
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        return {"deleted": True, "id": task_id}


@tool
def add_routine_block(day_of_week: str, start_time: str, activity: str, fixed: bool = False) -> dict:
    """Add a routine block, e.g. a class or a habit slot. day_of_week is
    'monday'..'sunday' or 'daily'. start_time is 'HH:MM' 24-hour. fixed=true
    means it can't move (like a class); fixed=false means it's movable."""
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO routine_blocks (day_of_week, start_time, activity, fixed) "
            "VALUES (?, ?, ?, ?)",
            (day_of_week, start_time, activity, int(fixed)),
        )
        return {"id": cur.lastrowid, "day_of_week": day_of_week, "activity": activity}


@tool
def list_routine_blocks(day_of_week: str = "") -> list[dict]:
    """List routine blocks, optionally filtered to one day_of_week
    ('monday'..'sunday' or 'daily'). Ordered by start_time."""
    query = "SELECT * FROM routine_blocks"
    params: tuple = ()
    if day_of_week:
        query += " WHERE day_of_week = ?"
        params = (day_of_week,)
    query += " ORDER BY start_time"
    with get_connection() as conn:
        return rows_to_dicts(conn.execute(query, params).fetchall())


@tool
def update_routine_block(
    block_id: int,
    day_of_week: str = "",
    start_time: str = "",
    activity: str = "",
    fixed: bool | None = None,
) -> dict:
    """Update a routine block. Leave a text field empty to keep it unchanged."""
    fields, values = [], []
    if day_of_week:
        fields.append("day_of_week = ?")
        values.append(day_of_week)
    if start_time:
        fields.append("start_time = ?")
        values.append(start_time)
    if activity:
        fields.append("activity = ?")
        values.append(activity)
    if fixed is not None:
        fields.append("fixed = ?")
        values.append(int(fixed))
    if not fields:
        return {"updated": False, "reason": "no fields provided"}
    values.append(block_id)
    with get_connection() as conn:
        conn.execute(f"UPDATE routine_blocks SET {', '.join(fields)} WHERE id = ?", values)
        return {"updated": True, "id": block_id}


@tool
def delete_routine_block(block_id: int) -> dict:
    """Permanently delete a routine block."""
    with get_connection() as conn:
        conn.execute("DELETE FROM routine_blocks WHERE id = ?", (block_id,))
        return {"deleted": True, "id": block_id}


ALL_TOOLS = [
    add_goal,
    list_goals,
    update_goal,
    delete_goal,
    add_task,
    list_tasks,
    update_task,
    delete_task,
    add_routine_block,
    list_routine_blocks,
    update_routine_block,
    delete_routine_block,
]
