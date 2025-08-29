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

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

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


def _get_current_prs(conn: PGConnection) -> Dict[str, List[Dict[str, Any]]]:
    """Return current tracked PRs for tracked exercises, grouped by exercise.

    Mirrors logic from the agent's get_current_prs but kept local to this server.
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Get tracked exercises
    cur.execute("SELECT exercise FROM tracked_exercises ORDER BY exercise")
    tracked_rows = cur.fetchall()
    tracked = [row["exercise"] for row in tracked_rows]
    if not tracked:
        return {}

    # Aggregate max loads by reps for each tracked exercise
    cur.execute(
        """
        SELECT e.name AS exercise,
               cs.reps_done AS reps,
               MAX(cs.load_done) AS max_load
        FROM completed_sets cs
        JOIN exercises e ON cs.exercise_id = e.id
        WHERE e.name = ANY(%s)
          AND cs.reps_done > 0
          AND cs.load_done > 0
        GROUP BY e.name, cs.reps_done
        ORDER BY e.name, cs.reps_done
        """,
        (tracked,),
    )
    rows = cur.fetchall()
    prs: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        prs.setdefault(row["exercise"], []).append({
            "reps": int(row["reps"]),
            "maxLoad": float(row["max_load"]) if row["max_load"] is not None else 0.0,
        })
    return prs


def COACH_ACTION_rewrite_todays_plan(user_intent: str) -> str:
    """Generate a proposed rewrite of today's workout plan as plain text.

    Context automatically includes:
    - Full weekly split (all 7 days)
    - Last 7 days of daily summaries and completed sets (organized by day)
    - Current PRs (tracked exercises)

    Output (text only):
    - A short 1-3 sentence summary first
    - Then each set on its own line using: "exercise | reps | load | rest_seconds"
      Use absolute loads only (no percentages). Rest is in seconds.

    NOTE: This tool does not modify the database. It only returns a plan proposal.
    """
    # Build context from DB
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Weekly split (all days)
        weekly_split_rows = COACH_GET_weekly_split()  # includes day_of_week when day is None
        days_by_index: Dict[int, List[Dict[str, Any]]] = {i: [] for i in range(7)}
        for row in weekly_split_rows:
            # row keys: day_of_week, exercise, reps, load, rest, order_num, relative
            idx = int(row.get("day_of_week", 0))
            days_by_index[idx].append(dict(row))

        # Split notes (single latest row)
        cur.execute(
            """
            SELECT notes FROM split_notes
            ORDER BY updated_at DESC
            LIMIT 1
            """
        )
        row = cur.fetchone()
        split_notes = (row["notes"] if row and row.get("notes") is not None else "").strip()

        # Past 7 days window
        window_start = date.today() - timedelta(days=7)

        # Daily summaries (last 7 days)
        cur.execute(
            """
            SELECT log_date, COALESCE(summary, '') AS summary
            FROM daily_logs
            WHERE log_date >= %s
            ORDER BY log_date
            """,
            (window_start.isoformat(),),
        )
        summaries = [dict(r) for r in cur.fetchall()]

        # Completed sets (last 7 days)
        cur.execute(
            """
            SELECT dl.log_date,
                   e.name AS exercise,
                   cs.reps_done,
                   cs.load_done,
                   cs.completed_at
            FROM completed_sets cs
            JOIN daily_logs dl ON cs.log_id = dl.id
            JOIN exercises e ON cs.exercise_id = e.id
            WHERE dl.log_date >= %s
            ORDER BY dl.log_date, cs.completed_at
            """,
            (window_start.isoformat(),),
        )
        completed_rows = [dict(r) for r in cur.fetchall()]
        completed_by_date: Dict[str, List[Dict[str, Any]]] = {}
        for r in completed_rows:
            key = str(r["log_date"])  # YYYY-MM-DD
            completed_by_date.setdefault(key, []).append(r)

        # Current PRs (tracked)
        prs = _get_current_prs(conn)
    finally:
        conn.close()

    # Build textual context blocks
    day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    def fmt_split_block() -> str:
        lines: List[str] = []
        for idx in range(7):
            lines.append(f"{day_names[idx]}:")
            day_sets = sorted(days_by_index.get(idx, []), key=lambda x: x.get("order_num", 0))
            if not day_sets:
                lines.append("  (no sets)")
            else:
                for s in day_sets:
                    rel = bool(s.get("relative", False))
                    lines.append(
                        f"  {s.get('order_num', '')}. {s['exercise']} | reps {s['reps']} | load {s['load']} | rest {s.get('rest', 60)}s | relative {str(rel).lower()}"
                    )
        return "\n".join(lines)

    def fmt_history_block() -> str:
        lines: List[str] = []
        # Build summary mapping keyed by date object
        summaries_by_date: Dict[date, str] = {}
        for s in summaries:
            d = s.get("log_date")
            if isinstance(d, datetime):
                d = d.date()
            elif not isinstance(d, date):
                try:
                    d = date.fromisoformat(str(d))
                except Exception:
                    # Skip unparseable entries
                    continue
            summaries_by_date[d] = s.get("summary", "")

        all_dates = sorted(summaries_by_date.keys())
        today_d = date.today()
        for d in all_dates:
            days_ago = (today_d - d).days
            dow = d.strftime("%A")
            lines.append(f"{dow} ({days_ago} days ago):")
            summary_text = summaries_by_date[d]
            if summary_text:
                lines.append(f"  summary: {summary_text}")
            # completed_by_date is keyed by ISO string
            day_completed = completed_by_date.get(d.isoformat(), [])
            if not day_completed:
                lines.append("  completed: (none)")
            else:
                for c in day_completed:
                    lines.append(f"  completed: {c['exercise']} | {c['reps_done']} | {c['load_done']}")
        return "\n".join(lines)

    def fmt_prs_block() -> str:
        lines: List[str] = []
        for exercise, entries in prs.items():
            parts = [f"{e['reps']} -> {e['maxLoad']}" for e in entries]
            joined = ", ".join(parts) if parts else "(none)"
            lines.append(f"{exercise}: {joined}")
        return "\n".join(lines) if lines else "(none)"

    weekly_split_text = fmt_split_block()
    history_text = fmt_history_block()
    prs_text = fmt_prs_block()
    split_notes_text = split_notes or "(none)"

    # Compose messages
    system_content = (
        "You are a strength coach generating TODAY's workout plan.\n"
        "Use the provided context: full weekly split, last 7 days of summaries and completed sets, and current PRs.\n"
        "Align with the weekly split's intent but adapt to the user's stated intent and recent recovery.\n\n"
        "Output requirements (STRICT):\n"
        "1) First, a 1-3 sentence summary for today's plan.\n"
        "2) Then each set on its own line in this exact format: exercise | reps | load | rest_seconds\n"
        "Rules: Use ABSOLUTE loads only (never percentages). rest_seconds is an integer number of seconds. No extra commentary, no headings, no code fences, no JSON."
    )

    human_content = (
        "Weekly Split (All Days):\n" + weekly_split_text + "\n\n"
        "Split Notes:\n" + split_notes_text + "\n\n"
        "Past 7 Days (Summaries + Completed Sets):\n" + history_text + "\n\n"
        "Current PRs (reps -> maxLoad):\n" + prs_text + "\n\n"
        "User intent:\n" + user_intent
    )

    # Model call (no post-processing)
    model_name = os.getenv("WORKOUT_PLANNER_MODEL", "gpt-5")
    chat = ChatOpenAI(model=model_name, openai_api_key=os.getenv("OPENAI_API_KEY"), temperature=0.3)
    resp = chat.invoke([SystemMessage(content=system_content), HumanMessage(content=human_content)])
    return resp.content if hasattr(resp, "content") else str(resp)


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
mcp.tool(COACH_ACTION_rewrite_todays_plan)
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
