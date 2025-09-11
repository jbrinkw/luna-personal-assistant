"""CoachByte — plan and track workouts.

Self-contained tool module that implements the direct tool code here.
Uses environment variables for DB connection (dotenv supported) and relies only
on local helpers, not scattered imports.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import date, timedelta, datetime, timezone
import os
import json
import subprocess

import psycopg2
import psycopg2.extras

try:  # Load .env if present
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()  # pragma: no cover
except Exception:  # pragma: no cover
    pass


# ---- Local helpers (no scattered imports) ----
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


def _require_env(keys: List[str]) -> None:
    missing = [k for k in keys if not os.getenv(k)]
    if missing and not os.getenv("DATABASE_URL"):
        raise RuntimeError(
            "Database configuration missing. Set DATABASE_URL or PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD."
        )


def _get_connection():
    url = os.getenv("DATABASE_URL")
    if url:
        return psycopg2.connect(url)
    _require_env(["PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD"])
    return psycopg2.connect(
        host=os.getenv("PGHOST"),
        port=int(os.getenv("PGPORT")),
        dbname=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
    )


def _get_exercise_id(conn, name: str) -> int:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id FROM exercises WHERE name = %s", (name,))
    row = cur.fetchone()
    if row:
        return row["id"]
    cur.execute("INSERT INTO exercises (name) VALUES (%s) RETURNING id", (name,))
    return cur.fetchone()["id"]


def _get_today_log_id(conn):
    today = date.today().isoformat()
    cur = conn.cursor()
    cur.execute("SELECT id FROM daily_logs WHERE log_date = %s", (today,))
    row = cur.fetchone()
    if row:
        return row[0]
    import uuid

    log_id = str(uuid.uuid4())
    cur.execute("INSERT INTO daily_logs (id, log_date) VALUES (%s, %s)", (log_id, today))
    conn.commit()
    return log_id


NAME = "CoachByte"


SYSTEM_PROMPT = """
Plan and track workouts for the user.

You can create a daily plan from a list of sets, retrieve today's plan in order,
complete the next planned set (optionally overriding reps or load), log extra
sets not in the plan, update a written summary for today, retrieve recent
history, and manage a weekly split schedule. You can also set and check a timer
for rest periods.

Tools are idempotent and validate reps/load ranges. Prefer using complete_planned_set
to advance the workout queue; use log_completed_set for unplanned sets.
"""


def COACHBYTE_UPDATE_new_daily_plan(items: List[Dict[str, Any]]):
    """Create today's daily workout plan with a list of planned sets.
    Example Prompt: Make a plan for today: bench press 10x135 at order 1; squat 8x185 at order 2.
    Example Response: Planned today's workout: bench press 10x135 (order 1); squat 8x185 (order 2).
    Example Args: {"items": [{"exercise": "string[exercise name]", "reps": int[number of reps], "load": float[weight], "rest": int[seconds], "order": int[sequence index]}]}
    """
    conn = _get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        log_id = _get_today_log_id(conn)

        cur.execute(
            "SELECT MIN(order_num) as min_order, MAX(order_num) as max_order FROM planned_sets WHERE log_id = %s",
            (log_id,),
        )
        result = cur.fetchone() or {}
        min_order = result.get("min_order") if result.get("min_order") is not None else 0
        max_order = result.get("max_order") if result.get("max_order") is not None else 0

        details: List[str] = []
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
            exercise_id = _get_exercise_id(conn, item["exercise"])

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
            details.append(f"{item['exercise']}, {reps} reps at {load:g} pounds as set {order_num}")
        conn.commit()
    finally:
        conn.close()
    summary = f"planned {len(items)} sets for today"
    if details:
        summary += ": " + "; ".join(details)
    return summary


def COACHBYTE_GET_today_plan() -> List[Dict[str, Any]]:
    """Return today's planned workout sets in order.
    Example Prompt: What's my workout plan for today?
    Example Response: Today's plan: bench press 10x135; squat 8x185.
    Example Args: {}
    """
    conn = _get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        log_id = _get_today_log_id(conn)
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
        return rows
    finally:
        conn.close()


def COACHBYTE_ACTION_complete_next_set(exercise: Optional[str] = None, reps: Optional[int] = None, load: Optional[float] = None) -> str:
    """Complete the next planned set (optionally specify exercise and/or override reps/load).
    Example Prompt: Complete my next set; if it's squats, do 8 reps instead.
    Example Response: Completed next set (squats): 8 reps.
    Example Args: {"exercise": "string[exercise name]", "reps": int[override reps], "load": float[override load]}
    """
    conn = _get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        log_id = _get_today_log_id(conn)

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
            return (f"No planned sets found for exercise: {exercise}" if exercise else "No planned sets remaining for today")

        actual_reps = reps if reps is not None else planned_set["reps"]
        actual_load = load if load is not None else planned_set["load"]
        if not (1 <= int(actual_reps) <= MAX_REPS):
            raise ValueError("reps out of range")
        if not (0 <= float(actual_load) <= MAX_LOAD):
            raise ValueError("load out of range")

        cur.execute(
            "INSERT INTO completed_sets (log_id, exercise_id, reps_done, load_done, completed_at) VALUES (%s, %s, %s, %s, %s)",
            (log_id, planned_set["exercise_id"], int(actual_reps), float(actual_load), datetime.now(timezone.utc)),
        )
        cur.execute("DELETE FROM planned_sets WHERE id = %s", (planned_set["id"],))
        conn.commit()

        rest_time = planned_set.get("rest", 60) or 60
        rest_info = ""
        if rest_time > 0:
            try:
                script_dir = os.path.join(os.path.dirname(__file__), "ui", "tools")
                timer_script = os.path.join(script_dir, "timer_temp.py")
                result = subprocess.run(["python", timer_script, "set", str(rest_time), "seconds"], capture_output=True, text=True, cwd=script_dir)
                if result.returncode == 0:
                    rest_info = f" Rest timer set for {rest_time} seconds."
                else:
                    rest_info = f" (Timer error: {result.stderr.strip()})"
            except Exception as e:  # pragma: no cover
                rest_info = f" (Timer error: {e})"

        result = f"Completed {planned_set['exercise']}: {int(actual_reps)} reps @ {float(actual_load)} load"
        if reps is not None or load is not None:
            result += f" (planned: {planned_set['reps']} reps @ {planned_set['load']} load)"
        result += rest_info
        return result
    finally:
        conn.close()


def COACHBYTE_ACTION_log_completed_set(exercise: str, reps: int, load: float) -> str:
    """Log an unplanned, completed set (not from the queue).
    Example Prompt: I did extra push-ups: 20 reps at bodyweight.
    Example Response: Logged set: push-ups, 20 reps at bodyweight.
    Example Args: {"exercise": "string[exercise name]", "reps": int[number of reps], "load": float[weight]}
    """
    if not (1 <= int(reps) <= MAX_REPS):
        raise ValueError("reps out of range")
    if not (0 <= float(load) <= MAX_LOAD):
        raise ValueError("load out of range")
    conn = _get_connection()
    try:
        cur = conn.cursor()
        log_id = _get_today_log_id(conn)
        exercise_id = _get_exercise_id(conn, exercise)
        cur.execute(
            "INSERT INTO completed_sets (log_id, exercise_id, reps_done, load_done, completed_at) VALUES (%s, %s, %s, %s, %s)",
            (log_id, exercise_id, int(reps), float(load), datetime.now(timezone.utc)),
        )
        conn.commit()
        return f"logged: {exercise}, {int(reps)} reps @ {float(load):g}"
    finally:
        conn.close()


def COACHBYTE_UPDATE_summary(text: str) -> str:
    """Update today's workout summary text.
    Example Prompt: Add summary: Great session, felt strong on bench.
    Example Response: summary updated
    Example Args: {"text": "string[summary text]"}
    """
    conn = _get_connection()
    try:
        cur = conn.cursor()
        log_id = _get_today_log_id(conn)
        cur.execute("UPDATE daily_logs SET summary = %s WHERE id = %s", (text, log_id))
        conn.commit()
        return "summary updated"
    finally:
        conn.close()


def COACHBYTE_GET_recent_history(days: int) -> List[Dict[str, Any]]:
    """Get recent workout history for N days (planned vs completed).
    Example Prompt: Show my last 7 days of workouts.
    Example Response: Recent 7-day workout summary returned.
    Example Args: {"days": int[number of days]}
    """
    conn = _get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        start = date.today() - timedelta(days=int(days))
        cur.execute(
            """
            SELECT dl.log_date, e.name as exercise, ps.reps, ps.load, cs.reps_done, cs.load_done
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
        return rows
    finally:
        conn.close()


def COACHBYTE_UPDATE_weekly_split_day(day: str, items: List[Dict[str, Any]]) -> str:
    """Replace the weekly split plan for a specific day with provided sets.
    Example Prompt: Set Monday split to bench 5x at 80% 1RM and squat 10x185.
    Example Response: split updated for monday with 2 sets
    Example Args: {"day": "monday", "items": [{"exercise": "bench press", "reps": 5, "load": 0.8, "relative": true, "rest": 90, "order": 1}, {"exercise": "squat", "reps": 10, "load": 185, "relative": false, "rest": 90, "order": 2}]}
    Usage: To specify a percent-of-1RM load, set "relative": true and pass "load" as a decimal fraction (e.g., 0.8 means 80% 1RM). For absolute loads (lbs/kg), set "relative": false (or omit) and pass a numeric load (e.g., 185).
    """
    key = (day or "").lower()
    if key not in DAY_MAP:
        raise ValueError("invalid day")
    day_num = DAY_MAP[key]
    conn = _get_connection()
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
            ex_id = _get_exercise_id(conn, item["exercise"])
            order_num = int(item.get("order", item.get("order_num", 1)))
            relative = bool(item.get("relative", False))
            cur.execute(
                "INSERT INTO split_sets (day_of_week, exercise_id, order_num, reps, load, rest, relative) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (day_num, ex_id, order_num, reps, load, rest, relative),
            )
        conn.commit()
        return f"split updated for {key} with {len(items)} sets"
    finally:
        conn.close()


def COACHBYTE_GET_weekly_split(day: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get weekly split plan (all days or a specific day).
    Example Prompt: What's my Wednesday split?
    Example Response: Wednesday split listed.
    Example Args: {"day": "string[day name]"}
    """
    conn = _get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if day is None:
            cur.execute(
                "SELECT day_of_week, e.name as exercise, reps, load, rest, order_num, relative FROM split_sets ss JOIN exercises e ON ss.exercise_id = e.id ORDER BY day_of_week, order_num"
            )
        else:
            key = day.lower()
            if key not in DAY_MAP:
                raise ValueError("invalid day")
            cur.execute(
                "SELECT e.name as exercise, reps, load, rest, order_num, relative FROM split_sets ss JOIN exercises e ON ss.exercise_id = e.id WHERE day_of_week = %s ORDER BY order_num",
                (DAY_MAP[key],),
            )
        rows = [dict(row) for row in cur.fetchall()]
        return rows
    finally:
        conn.close()


def COACHBYTE_ACTION_set_timer(minutes: int) -> str:
    """Set a rest/workout timer in minutes (1–180).
    Example Prompt: Set a 3 minute rest timer.
    Example Response: Timer set for 3 minutes
    Example Args: {"minutes": int[1-180]}
    """
    if not (1 <= int(minutes) <= 180):
        raise ValueError("Timer duration must be between 1 and 180 minutes")
    try:
        script_dir = os.path.join(os.path.dirname(__file__), "ui", "tools")
        timer_script = os.path.join(script_dir, "timer_temp.py")
        result = subprocess.run(["python", timer_script, "set", str(int(minutes))], capture_output=True, text=True, cwd=script_dir)
        if result.returncode == 0:
            return f"Timer set for {int(minutes)} minutes"
        else:
            return f"Timer error: {result.stderr.strip()}"
    except Exception as e:  # pragma: no cover
        return f"Timer error: {e}"


def COACHBYTE_GET_timer() -> Dict[str, Any]:
    """Get current timer status and remaining time.
    Example Prompt: How much time is left on my rest timer?
    Example Response: {"status": "running", "remaining_seconds": 120}
    Example Args: {}
    """
    try:
        script_dir = os.path.join(os.path.dirname(__file__), "ui", "tools")
        timer_script = os.path.join(script_dir, "timer_temp.py")
        result = subprocess.run(["python", timer_script, "get"], capture_output=True, text=True, cwd=script_dir)
        if result.returncode == 0:
            try:
                timer_data = json.loads(result.stdout.strip())
                return timer_data
            except json.JSONDecodeError:
                return {"status": "no_timer", "message": result.stdout.strip()}
        else:
            return {"status": "error", "message": f"Timer error: {result.stderr.strip()}"}
    except Exception as e:  # pragma: no cover
        return {"status": "error", "message": f"Timer error: {e}"}


TOOLS = [
    COACHBYTE_UPDATE_new_daily_plan,
    COACHBYTE_GET_today_plan,
    COACHBYTE_ACTION_complete_next_set,
    COACHBYTE_ACTION_log_completed_set,
    COACHBYTE_UPDATE_summary,
    COACHBYTE_GET_recent_history,
    COACHBYTE_UPDATE_weekly_split_day,
    COACHBYTE_GET_weekly_split,
    COACHBYTE_ACTION_set_timer,
    COACHBYTE_GET_timer,
]





