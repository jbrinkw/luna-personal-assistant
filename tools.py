from typing import List, Dict, Any
from datetime import date, timedelta
import sqlite3

from db import get_connection, get_today_log_id

# Helper validation
MAX_LOAD = 2000
MAX_REPS = 100


def _get_exercise_id(conn: sqlite3.Connection, name: str) -> int:
    cur = conn.execute("SELECT id FROM exercises WHERE name = ?", (name,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur = conn.execute("INSERT INTO exercises (name) VALUES (?)", (name,))
    return cur.lastrowid


def new_daily_plan(items: List[Dict[str, Any]]):
    """Create today's daily log and planned sets"""
    conn = get_connection()
    try:
        log_id = get_today_log_id(conn)
        for item in items:
            reps = int(item["reps"])
            load = float(item["load"])
            if not (1 <= reps <= MAX_REPS):
                raise ValueError("reps out of range")
            if not (0 <= load <= MAX_LOAD):
                raise ValueError("load out of range")
            exercise_id = _get_exercise_id(conn, item["exercise"])
            order_num = int(item["order"])
            conn.execute(
                "INSERT INTO planned_sets (log_id, exercise_id, order_num, reps, load) VALUES (?, ?, ?, ?, ?)",
                (log_id, exercise_id, order_num, reps, load),
            )
        conn.commit()
    finally:
        conn.close()
    return f"planned {len(items)} sets for today"


def get_today_plan() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        log_id = get_today_log_id(conn)
        cur = conn.execute(
            "SELECT e.name as exercise, reps, load, order_num FROM planned_sets ps JOIN exercises e ON ps.exercise_id = e.id WHERE log_id = ? ORDER BY order_num",
            (log_id,),
        )
        rows = [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
    return rows


def log_completed_set(exercise: str, reps: int, load: float):
    if not (1 <= reps <= MAX_REPS):
        raise ValueError("reps out of range")
    if not (0 <= load <= MAX_LOAD):
        raise ValueError("load out of range")
    conn = get_connection()
    try:
        log_id = get_today_log_id(conn)
        exercise_id = _get_exercise_id(conn, exercise)
        conn.execute(
            "INSERT INTO completed_sets (log_id, exercise_id, reps_done, load_done) VALUES (?, ?, ?, ?)",
            (log_id, exercise_id, reps, load),
        )
        conn.commit()
    finally:
        conn.close()
    return "logged"


def update_summary(text: str):
    conn = get_connection()
    try:
        log_id = get_today_log_id(conn)
        conn.execute("UPDATE daily_logs SET summary = ? WHERE id = ?", (text, log_id))
        conn.commit()
    finally:
        conn.close()
    return "summary updated"


def get_recent_history(days: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        start = date.today() - timedelta(days=days)
        cur = conn.execute(
            """
            SELECT dl.log_date, e.name as exercise, ps.reps, ps.load, cs.reps_done, cs.load_done
            FROM planned_sets ps
            JOIN daily_logs dl ON ps.log_id = dl.id
            JOIN exercises e ON ps.exercise_id = e.id
            LEFT JOIN completed_sets cs ON cs.log_id = ps.log_id AND cs.exercise_id = ps.exercise_id
            WHERE dl.log_date >= ?
            ORDER BY dl.log_date, ps.order_num
            """,
            (start.isoformat(),),
        )
        rows = [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
    return rows


def run_sql(query: str, params: Dict[str, Any] = None, confirm: bool = False):
    """Run arbitrary SQL. Reject mutations unless confirm=True"""
    params = params or {}
    lowered = query.strip().lower()
    if not lowered.startswith("select") and not confirm:
        raise ValueError("updates require confirm=True")
    conn = get_connection()
    try:
        cur = conn.execute(query, params)
        if lowered.startswith("select"):
            rows = [dict(row) for row in cur.fetchall()]
        else:
            conn.commit()
            rows = {"rows_affected": cur.rowcount}
    finally:
        conn.close()
    return rows


def arbitrary_update(query: str, params: Dict[str, Any] = None):
    return run_sql(query, params=params, confirm=True)
