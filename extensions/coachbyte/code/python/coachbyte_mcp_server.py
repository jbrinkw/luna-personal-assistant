"""Run the CoachByte MCP server exposing all workout tools (baked-in)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import json
import os
from datetime import date, datetime, timedelta, timezone

import psycopg2.extras
from psycopg2.extensions import connection as PGConnection
from fastmcp import FastMCP

from db import get_connection, get_today_log_id


# Create MCP server
mcp = FastMCP("CoachByte Tools")


# Shared constants and helpers
MAX_LOAD = 2000
MAX_REPS = 100

DAY_MAP = {
    "sunday": 0,
    "monday": 1,
    "tuesday": 2,
    "wednesday": 3,
    "thursday": 4,
    "friday": 5,
    "saturday": 6,
}


def _get_exercise_id(conn: PGConnection, name: str) -> int:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id FROM exercises WHERE name = %s", (name,))
    row = cur.fetchone()
    if row:
        return row["id"]
    cur.execute("INSERT INTO exercises (name) VALUES (%s) RETURNING id", (name,))
    return cur.fetchone()["id"]


def COACH_UPDATE_new_daily_plan(items: List[Dict[str, Any]]) -> str:
    """Create today's daily workout plan with a list of planned sets.

    Parameters:
    - items: List of dicts with keys:
      - exercise (str)
      - reps (int)
      - load (float)
      - order (int): 0 append, -1 prepend, or explicit order
      - rest (int, optional): seconds (0-600), default 60

    Returns a success message.
    """
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        log_id = get_today_log_id(conn)

        # Determine current min/max order to support prepend/append
        cur.execute(
            "SELECT MIN(order_num) as min_order, MAX(order_num) as max_order FROM planned_sets WHERE log_id = %s",
            (log_id,),
        )
        result = cur.fetchone() or {"min_order": 0, "max_order": 0}
        min_order = result["min_order"] if result["min_order"] is not None else 0
        max_order = result["max_order"] if result["max_order"] is not None else 0

        for item in items:
            reps = int(item["reps"])
            load = float(item["load"])
            rest = int(item.get("rest", 60))
            if not (1 <= reps <= MAX_REPS):
                raise ValueError("reps out of range")
            if not (0 <= load <= MAX_LOAD):
                raise ValueError("load out of range")
            if not (0 <= rest <= 600):
                raise ValueError("rest time out of range")

            exercise_id = _get_exercise_id(conn, str(item["exercise"]))

            order_raw = int(item["order"]) if "order" in item else int(item.get("order_num", 0))
            if order_raw == 0:
                order_num = max_order + 1
                max_order = order_num
            elif order_raw == -1:
                order_num = min_order - 1
                min_order = order_num
            else:
                order_num = order_raw

            cur.execute(
                "INSERT INTO planned_sets (log_id, exercise_id, order_num, reps, load, rest) VALUES (%s, %s, %s, %s, %s, %s)",
                (log_id, exercise_id, order_num, reps, load, rest),
            )
        conn.commit()
    finally:
        conn.close()
    return f"planned {len(items)} sets for today"


def COACH_GET_today_plan() -> List[Dict[str, Any]]:
    """Retrieve today's planned workout sets in order."""
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        log_id = get_today_log_id(conn)
        cur.execute(
            """
            SELECT e.name as exercise, reps, load, rest, order_num
            FROM planned_sets ps
            JOIN exercises e ON ps.exercise_id = e.id
            WHERE log_id = %s
            ORDER BY order_num
            """,
            (log_id,),
        )
        rows = [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
    return rows


def COACH_UPDATE_log_completed_set(exercise: str, reps: int, load: float) -> str:
    """Record an unplanned set completion (not part of today's plan)."""
    if not (1 <= int(reps) <= MAX_REPS):
        raise ValueError("reps out of range")
    if not (0 <= float(load) <= MAX_LOAD):
        raise ValueError("load out of range")
    conn = get_connection()
    try:
        cur = conn.cursor()
        log_id = get_today_log_id(conn)
        exercise_id = _get_exercise_id(conn, exercise)
        cur.execute(
            "INSERT INTO completed_sets (log_id, exercise_id, reps_done, load_done, completed_at) VALUES (%s, %s, %s, %s, %s)",
            (log_id, exercise_id, int(reps), float(load), datetime.now(timezone.utc)),
        )
        conn.commit()
    finally:
        conn.close()
    return "logged"


def COACH_UPDATE_complete_planned_set(
    exercise: Optional[str] = None,
    reps: Optional[int] = None,
    load: Optional[float] = None,
) -> str:
    """Complete the next planned set in the queue, with optional overrides.

    - If exercise is provided, complete the first planned set for that exercise.
    - If reps/load are provided, they override the planned values.
    - Records completion referencing planned_set_id (does not delete planned set).
    """
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        log_id = get_today_log_id(conn)

        if exercise:
            cur.execute(
                """
                SELECT ps.id, ps.exercise_id, e.name as exercise, ps.reps, ps.load, ps.rest, ps.order_num
                FROM planned_sets ps
                JOIN exercises e ON ps.exercise_id = e.id
                WHERE ps.log_id = %s AND e.name = %s
                ORDER BY ps.order_num
                LIMIT 1
                """,
                (log_id, exercise),
            )
        else:
            cur.execute(
                """
                SELECT ps.id, ps.exercise_id, e.name as exercise, ps.reps, ps.load, ps.rest, ps.order_num
                FROM planned_sets ps
                JOIN exercises e ON ps.exercise_id = e.id
                WHERE ps.log_id = %s
                ORDER BY ps.order_num
                LIMIT 1
                """,
                (log_id,),
            )

        planned_set = cur.fetchone()
        if not planned_set:
            return (
                f"No planned sets found for exercise: {exercise}" if exercise else "No planned sets remaining for today"
            )

        actual_reps = int(reps) if reps is not None else int(planned_set["reps"])  # conversion, not cast
        actual_load = float(load) if load is not None else float(planned_set["load"])  # conversion, not cast
        if not (1 <= actual_reps <= MAX_REPS):
            raise ValueError("reps out of range")
        if not (0 <= actual_load <= MAX_LOAD):
            raise ValueError("load out of range")

        cur.execute(
            """
            INSERT INTO completed_sets (log_id, exercise_id, planned_set_id, reps_done, load_done, completed_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                log_id,
                planned_set["exercise_id"],
                planned_set["id"],
                actual_reps,
                actual_load,
                datetime.now(timezone.utc),
            ),
        )
        conn.commit()

        # Optional: set a rest timer based on planned rest
        rest_time = int(planned_set.get("rest", 60))
        rest_info = ""
        if rest_time > 0:
            try:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                timer_script = os.path.join(script_dir, "timer_temp.py")
                import subprocess

                result = subprocess.run(
                    ["python", timer_script, "set", str(rest_time), "seconds"],
                    capture_output=True,
                    text=True,
                    cwd=script_dir,
                )
                if result.returncode == 0:
                    rest_info = f" Rest timer set for {rest_time} seconds."
                else:
                    rest_info = f" (Timer error: {result.stderr.strip()})"
            except Exception as e:  # noqa: BLE001
                rest_info = f" (Timer error: {e})"

        result_msg = (
            f"Completed {planned_set['exercise']}: {actual_reps} reps @ {actual_load} load"
        )
        if reps is not None or load is not None:
            result_msg += (
                f" (planned: {planned_set['reps']} reps @ {planned_set['load']} load)"
            )
        result_msg += rest_info
        return result_msg
    finally:
        conn.close()


def COACH_UPDATE_summary(text: str) -> str:
    """Update today's workout summary text."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        log_id = get_today_log_id(conn)
        cur.execute("UPDATE daily_logs SET summary = %s WHERE id = %s", (text, log_id))
        conn.commit()
    finally:
        conn.close()
    return "summary updated"


def COACH_GET_recent_history(days: int) -> List[Dict[str, Any]]:
    """Retrieve recent workout history for the last N days."""
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        start = date.today() - timedelta(days=int(days))
        cur.execute(
            """
            SELECT dl.log_date, e.name as exercise, ps.reps, ps.load, ps.rest,
                   cs.reps_done, cs.load_done
            FROM planned_sets ps
            JOIN daily_logs dl ON ps.log_id = dl.id
            JOIN exercises e ON ps.exercise_id = e.id
            LEFT JOIN completed_sets cs ON cs.planned_set_id = ps.id
            WHERE dl.log_date >= %s
            ORDER BY dl.log_date, ps.order_num
            """,
            (start.isoformat(),),
        )
        rows = [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
    return rows


def COACH_UPDATE_set_weekly_split_day(day: str, items: List[Dict[str, Any]]) -> str:
    """Replace the weekly split plan for a specific day.

    Each item requires: exercise (str), reps (int), load (float), order (int), rest (int optional), relative (bool optional).
    """
    key = day.lower()
    if key not in DAY_MAP:
        raise ValueError("invalid day")
    day_num = DAY_MAP[key]
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM split_sets WHERE day_of_week = %s", (day_num,))
        for item in items:
            reps = int(item["reps"])
            load = float(item["load"])
            rest = int(item.get("rest", 60))
            if not (1 <= reps <= MAX_REPS):
                raise ValueError("reps out of range")
            if not (0 <= load <= MAX_LOAD):
                raise ValueError("load out of range")
            if not (0 <= rest <= 600):
                raise ValueError("rest out of range")
            ex_id = _get_exercise_id(conn, item["exercise"])  # trimmed trailing space
            order_num = int(item.get("order", item.get("order_num", 1)))
            relative = bool(item.get("relative", False))
            cur.execute(
                "INSERT INTO split_sets (day_of_week, exercise_id, order_num, reps, load, rest, relative) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (day_num, ex_id, order_num, reps, load, rest, relative),
            )
        conn.commit()
    finally:
        conn.close()
    return f"split updated for {key} with {len(items)} sets"


def COACH_GET_weekly_split(day: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve weekly split plan. If day is provided, limit to that day."""
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if day is None:
            cur.execute(
                """
                SELECT day_of_week, e.name as exercise, reps, load, rest, order_num, relative
                FROM split_sets ss
                JOIN exercises e ON ss.exercise_id = e.id
                ORDER BY day_of_week, order_num
                """
            )
        else:
            key = day.lower()
            if key not in DAY_MAP:
                raise ValueError("invalid day")
            cur.execute(
                """
                SELECT e.name as exercise, reps, load, rest, order_num, relative
                FROM split_sets ss
                JOIN exercises e ON ss.exercise_id = e.id
                WHERE day_of_week = %s
                ORDER BY order_num
                """,
                (DAY_MAP[key],),
            )
        rows = [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
    return rows


def COACH_ACTION_set_timer(minutes: int) -> str:
    """Set a rest/workout timer in minutes (1-180)."""
    duration = int(minutes)
    if not (1 <= duration <= 180):
        raise ValueError("Timer duration must be between 1 and 180 minutes")
    try:
        import subprocess

        script_dir = os.path.dirname(os.path.abspath(__file__))
        timer_script = os.path.join(script_dir, "timer_temp.py")
        result = subprocess.run(
            ["python", timer_script, "set", str(duration)],
            capture_output=True,
            text=True,
            cwd=script_dir,
        )
        if result.returncode == 0:
            return f"Timer set for {duration} minutes"
        return f"Timer error: {result.stderr.strip()}"
    except Exception as e:  # noqa: BLE001
        return f"Timer error: {e}"


def COACH_GET_timer() -> Dict[str, Any]:
    """Get current timer status and remaining time."""
    try:
        import subprocess

        script_dir = os.path.dirname(os.path.abspath(__file__))
        timer_script = os.path.join(script_dir, "timer_temp.py")
        result = subprocess.run(
            ["python", timer_script, "get"],
            capture_output=True,
            text=True,
            cwd=script_dir,
        )
        if result.returncode == 0:
            try:
                return json.loads(result.stdout.strip())
            except json.JSONDecodeError:
                return {"status": "no_timer", "message": result.stdout.strip()}
        else:
            return {"status": "error", "message": f"Timer error: {result.stderr.strip()}"}
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "message": f"Timer error: {e}"}


# Register all tools with MCP
mcp.tool(COACH_UPDATE_new_daily_plan)
mcp.tool(COACH_GET_today_plan)
mcp.tool(COACH_UPDATE_log_completed_set)
mcp.tool(COACH_UPDATE_complete_planned_set)
mcp.tool(COACH_UPDATE_summary)
mcp.tool(COACH_GET_recent_history)
mcp.tool(COACH_UPDATE_set_weekly_split_day)
mcp.tool(COACH_GET_weekly_split)
mcp.tool(COACH_ACTION_set_timer)
mcp.tool(COACH_GET_timer)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the aggregated CoachByte MCP server"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host (default 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8053,
        help="Port (default 8053)",
    )
    args = parser.parse_args()

    url = (
        f"http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}/sse"
    )
    print(f"[CoachByte] Running via SSE at {url}")

    mcp.run(transport="sse", host=args.host, port=args.port)
