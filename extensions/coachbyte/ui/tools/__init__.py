"""Application tools for workout tracking agent."""

from typing import List, Dict, Any, Optional
from datetime import date, timedelta, datetime, timezone
import psycopg2.extras

try:
    # Prefer absolute import from repo root
    from extensions.coachbyte.code.python.db import get_connection, get_today_log_id
except ModuleNotFoundError:  # pragma: no cover
    # Fallback for environments running this module directly
    import sys as _sys
    import os as _os
    _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..', 'code', 'python')))
    from db import get_connection, get_today_log_id  # type: ignore


def get_corrected_time():
    """Get the current UTC time"""
    return datetime.now(timezone.utc)

# Helper validation
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


def _get_exercise_id(conn, name: str) -> int:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id FROM exercises WHERE name = %s", (name,))
    row = cur.fetchone()
    if row:
        return row['id']
    cur.execute("INSERT INTO exercises (name) VALUES (%s) RETURNING id", (name,))
    return cur.fetchone()['id']


def new_daily_plan(items: List[Dict[str, Any]]):
    """Create today's daily workout plan with a list of planned sets.
    
    Parameters:
    - items: List of dictionaries, each containing:
        - exercise (str): Exercise name (e.g., "bench press", "squat", "pull-ups")
        - reps (int): Number of repetitions (1-100)
        - load (float): Weight in pounds (0-2000). Use 0 for bodyweight exercises
        - order (int): Set order/sequence number. Special values:
          - Normal: 1, 2, 3, etc. for specific positions
          - 0: Add to back of queue (after all existing sets)
          - -1: Add to front of queue (before all existing sets)
        - rest (int, optional): Rest time in seconds (0-600). Defaults to 60 seconds
    
    Example:
    items = [
        {"exercise": "bench press", "reps": 10, "load": 135, "order": 1, "rest": 90},
        {"exercise": "squat", "reps": 8, "load": 185, "order": 0, "rest": 120},  # Goes to back
        {"exercise": "pull-ups", "reps": 6, "load": 0, "order": -1, "rest": 60}  # Goes to front
    ]
    
    Returns: Success message with number of sets planned
    """
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        log_id = get_today_log_id(conn)
        
        # Get current min and max order numbers for queue positioning
        cur.execute("SELECT MIN(order_num) as min_order, MAX(order_num) as max_order FROM planned_sets WHERE log_id = %s", (log_id,))
        result = cur.fetchone()
        min_order = result['min_order'] if result['min_order'] is not None else 0
        max_order = result['max_order'] if result['max_order'] is not None else 0
        
        details: List[str] = []
        for item in items:
            reps = int(item["reps"])
            load = float(item["load"])
            rest = int(item.get("rest", 60))  # Default to 60 seconds if not provided
            if not (1 <= reps <= MAX_REPS):
                raise ValueError("reps out of range")
            if not (0 <= load <= MAX_LOAD):
                raise ValueError("load out of range")
            if not (0 <= rest <= 600):  # Max 10 minutes rest
                raise ValueError("rest time out of range")
            exercise_id = _get_exercise_id(conn, item["exercise"])
            
            # Handle special order values
            order_raw = int(item["order"])
            if order_raw == 0:
                # Add to back of queue
                order_num = max_order + 1
                max_order = order_num  # Update for next iteration
            elif order_raw == -1:
                # Add to front of queue
                order_num = min_order - 1
                min_order = order_num  # Update for next iteration
            else:
                # Normal order number
                order_num = order_raw
            
            cur.execute(
                "INSERT INTO planned_sets (log_id, exercise_id, order_num, reps, load, rest) VALUES (%s, %s, %s, %s, %s, %s)",
                (log_id, exercise_id, order_num, reps, load, rest),
            )
            # Build human-readable detail for this set
            details.append(f"{item['exercise']}, {reps} reps at {load:g} pounds as set {order_num}")
        conn.commit()
    finally:
        conn.close()
    summary = f"planned {len(items)} sets for today"
    if details:
        summary += ": " + "; ".join(details)
    return summary


def get_today_plan() -> List[Dict[str, Any]]:
    """Retrieve today's planned workout sets in order.
    
    No parameters required.
    
    Returns: List of dictionaries, each containing:
    - exercise (str): Exercise name
    - reps (int): Planned repetitions
    - load (float): Planned weight in pounds
    - rest (int): Rest time in seconds
    - order_num (int): Set sequence number
    
    Example return:
    [
        {"exercise": "bench press", "reps": 10, "load": 135.0, "rest": 90, "order_num": 1},
        {"exercise": "squat", "reps": 8, "load": 185.0, "rest": 120, "order_num": 2}
    ]
    """
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        log_id = get_today_log_id(conn)
        cur.execute(
            "SELECT e.name as exercise, reps, load, rest, order_num FROM planned_sets ps JOIN exercises e ON ps.exercise_id = e.id WHERE log_id = %s ORDER BY order_num",
            (log_id,),
        )
        rows = [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
    return rows


def log_completed_set(exercise: str, reps: int, load: float):
    """Record a completed set that was NOT part of the planned workout (for extra/unplanned sets).
    
    IMPORTANT: Use complete_planned_set() instead if completing a set from today's plan.
    This function is for logging additional sets that weren't planned.
    
    Parameters:
    - exercise (str): Exercise name (e.g., "bench press", "deadlift", "push-ups")
    - reps (int): Number of repetitions completed (1-100)
    - load (float): Weight used in pounds (0-2000). Use 0 for bodyweight exercises
    
    Examples:
    - log_completed_set("push-ups", 20, 0)  # Bodyweight exercise
    - log_completed_set("bench press", 8, 155)  # Weighted exercise
    
    Returns: "logged" on success
    """
    if not (1 <= reps <= MAX_REPS):
        raise ValueError("reps out of range")
    if not (0 <= load <= MAX_LOAD):
        raise ValueError("load out of range")
    conn = get_connection()
    try:
        cur = conn.cursor()
        log_id = get_today_log_id(conn)
        exercise_id = _get_exercise_id(conn, exercise)
        cur.execute(
            "INSERT INTO completed_sets (log_id, exercise_id, reps_done, load_done, completed_at) VALUES (%s, %s, %s, %s, %s)",
            (log_id, exercise_id, reps, load, datetime.now(timezone.utc)),
        )
        conn.commit()
    finally:
        conn.close()
    return f"logged: {exercise}, {reps} reps @ {load:g}"


def complete_planned_set(exercise: Optional[str] = None, reps: Optional[int] = None, load: Optional[float] = None):
    """Complete the next planned set in the workout queue, with optional overrides.
    
    This is the PRIMARY function for completing planned sets during a workout.
    It finds the next set in the queue and marks it as completed.
    
    Parameters (all optional):
    - exercise (str, optional): Specific exercise name to complete. If not provided, 
      completes the next set in order regardless of exercise
    - reps (int, optional): Override planned reps with actual reps performed (1-100).
      If not provided, uses the planned reps
    - load (float, optional): Override planned weight with actual weight used (0-2000).
      If not provided, uses the planned weight
    
    Behavior:
    - With no parameters: Completes next set in queue with planned values
    - With exercise only: Finds first planned set for that exercise
    - With overrides: Uses provided values instead of planned values
    
    Examples:
    - complete_planned_set()  # Complete next set with planned values
    - complete_planned_set(reps=8)  # Complete next set but only did 8 reps
    - complete_planned_set(exercise="squat")  # Complete next squat set
    - complete_planned_set(exercise="bench press", reps=9, load=140)  # Override both
    
    Returns: Detailed completion message with actual values and timer info
    """
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        log_id = get_today_log_id(conn)
        
        # Find the next planned set to complete (same logic as UI)
        if exercise:
            # Complete specific exercise - find first planned set for that exercise
            cur.execute("""
                SELECT ps.id, ps.exercise_id, e.name as exercise, ps.reps, ps.load, ps.rest, ps.order_num
                FROM planned_sets ps
                JOIN exercises e ON ps.exercise_id = e.id
                WHERE ps.log_id = %s AND e.name = %s
                ORDER BY ps.order_num
                LIMIT 1
            """, (log_id, exercise))
        else:
            # Complete next planned set in order (first in queue, same as UI)
            cur.execute("""
                SELECT ps.id, ps.exercise_id, e.name as exercise, ps.reps, ps.load, ps.rest, ps.order_num
                FROM planned_sets ps
                JOIN exercises e ON ps.exercise_id = e.id
                WHERE ps.log_id = %s
                ORDER BY ps.order_num
                LIMIT 1
            """, (log_id,))
        
        planned_set = cur.fetchone()
        if not planned_set:
            if exercise:
                return f"No planned sets found for exercise: {exercise}"
            else:
                return "No planned sets remaining for today"
        
        # Use planned values as defaults, override if provided
        actual_reps = reps if reps is not None else planned_set['reps']
        actual_load = load if load is not None else planned_set['load']
        
        # Validate overrides
        if not (1 <= actual_reps <= MAX_REPS):
            raise ValueError("reps out of range")
        if not (0 <= actual_load <= MAX_LOAD):
            raise ValueError("load out of range")
        
        # Record the completion (without planned_set_id to avoid foreign key constraint)
        # Since we're deleting the planned_set, we don't need to maintain the reference
        cur.execute(
            "INSERT INTO completed_sets (log_id, exercise_id, reps_done, load_done, completed_at) VALUES (%s, %s, %s, %s, %s)",
            (log_id, planned_set['exercise_id'], actual_reps, actual_load, datetime.now(timezone.utc)),
        )
        
        # Delete the completed planned set (same as UI behavior)
        # No foreign key constraint issue since we didn't store the planned_set_id reference
        cur.execute(
            "DELETE FROM planned_sets WHERE id = %s",
            (planned_set['id'],)
        )
        
        conn.commit()
        
        # Set timer for rest period if there's a rest time
        rest_time = planned_set.get('rest', 60)  # Default to 60 seconds
        if rest_time > 0:
            try:
                import subprocess
                import os
                # Ensure we're in the correct directory for the timer script
                script_dir = os.path.dirname(os.path.abspath(__file__))
                timer_script = os.path.join(script_dir, 'timer_temp.py')
                result = subprocess.run(['python', timer_script, 'set', str(rest_time), 'seconds'], 
                                       capture_output=True, text=True, cwd=script_dir)
                if result.returncode == 0:
                    rest_info = f" Rest timer set for {rest_time} seconds."
                else:
                    rest_info = f" (Timer error: {result.stderr.strip()})"
            except Exception as e:
                rest_info = f" (Timer error: {e})"
        else:
            rest_info = ""
        
        # Return completion summary
        result = f"Completed {planned_set['exercise']}: {actual_reps} reps @ {actual_load} load"
        if reps is not None or load is not None:
            result += f" (planned: {planned_set['reps']} reps @ {planned_set['load']} load)"
        result += rest_info
        return result
        
    finally:
        conn.close()


def update_summary(text: str):
    """Update today's workout summary with a descriptive text.
    
    This saves a summary of how the workout went, feelings, progress notes, etc.
    
    Parameters:
    - text (str): Summary text describing the workout. Can be any length.
      Examples: "Great session, felt strong", "Tough leg day, form was good", 
      "PRed on bench press today!"
    
    Examples:
    - update_summary("Excellent upper body session. Hit all planned sets.")
    - update_summary("Struggled with squats today, but completed the workout.")
    - update_summary("New PR on deadlift! 315x5 felt smooth.")
    
    Returns: "summary updated" on success
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        log_id = get_today_log_id(conn)
        cur.execute("UPDATE daily_logs SET summary = %s WHERE id = %s", (text, log_id))
        conn.commit()
    finally:
        conn.close()
    return "summary updated"


def get_recent_history(days: int) -> List[Dict[str, Any]]:
    """Retrieve workout history for the specified number of recent days.
    
    Shows both planned and completed sets to track progress and adherence.
    
    Parameters:
    - days (int): Number of days to look back (1-30 recommended)
    
    Returns: List of dictionaries, each containing:
    - log_date (str): Date of the workout (YYYY-MM-DD format)
    - exercise (str): Exercise name
    - reps (int): Planned repetitions (if planned)
    - load (float): Planned weight in pounds (if planned)
    - reps_done (int): Actual repetitions completed (if completed)
    - load_done (float): Actual weight used in pounds (if completed)
    
    Examples:
    - get_recent_history(3)  # Last 3 days
    - get_recent_history(7)  # Last week
    - get_recent_history(14) # Last 2 weeks
    
    Use this to analyze progress, identify patterns, or review recent workouts.
    """
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        start = date.today() - timedelta(days=days)
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
    finally:
        conn.close()
    return rows


def set_weekly_split_day(day: str, items: List[Dict[str, Any]]):
    """Replace the weekly split plan for the specified day.

    Parameters:
    - day (str): Day of week (e.g., "monday", "tuesday")
    - items: list of planned sets with keys: 
        - exercise (str): name of the exercise
        - reps (int): number of repetitions
        - load (float): weight in pounds, or percentage if relative is true
        - order (int): sequence number for the set
        - rest (int, optional): rest time in seconds
        - relative (bool, optional): if true, load is a percentage of 1-rep max. Defaults to false.

    Example:
    set_weekly_split_day(
        "monday", 
        [
            {"exercise": "bench press", "reps": 5, "load": 80, "order": 1, "relative": True},
            {"exercise": "squat", "reps": 10, "load": 185, "order": 2}
        ]
    )

    Returns success message with number of sets stored.
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
            ex_id = _get_exercise_id(conn, item["exercise"])
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


def get_weekly_split(day: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve the weekly split plan.

    Parameters:
    - day (str, optional): Specific day name to fetch. If omitted, returns all days.

    Returns list of sets with exercise, reps, load, rest and order_num.
    """
    conn = get_connection()
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
    finally:
        conn.close()
    return rows


def _execute_sql(query: str, params: Optional[Dict[str, Any]] = None, confirm: bool = False):
    """Internal SQL execution function"""
    if params is None:
        params = {}
    lowered = query.strip().lower()
    if not lowered.startswith("select") and not confirm:
        raise ValueError("updates require confirm=True")
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Convert params dict to list if needed for PostgreSQL
        if params:
            # PostgreSQL uses %(name)s format for named parameters
            cur.execute(query, params)
        else:
            cur.execute(query)
            
        if lowered.startswith("select"):
            rows = [dict(row) for row in cur.fetchall()]
        else:
            conn.commit()
            rows = {"rows_affected": cur.rowcount}
    finally:
        conn.close()
    return rows


# def run_sql(query: str, params: Optional[Dict[str, Any]] = None, confirm: bool = False):
#     """Execute SQL queries against the workout database.
    
#     SELECT queries run automatically. UPDATE/INSERT/DELETE require confirm=True for safety.
    
#     Parameters:
#     - query (str): SQL query to execute. Use %(param_name)s for parameter placeholders
#     - params (dict, optional): Dictionary of named parameters for the query
#     - confirm (bool): Must be True for UPDATE/INSERT/DELETE queries. Defaults to False
    
#     Examples:
#     - run_sql("SELECT * FROM exercises")  # Simple select
#     - run_sql("SELECT * FROM exercises WHERE name = %(exercise)s", {"exercise": "squat"})
#     - run_sql("UPDATE exercises SET name = %(new_name)s WHERE id = %(id)s", 
#               {"new_name": "back squat", "id": 1}, confirm=True)  # Requires confirm=True
    
#     Returns: 
#     - For SELECT: List of dictionaries with query results
#     - For UPDATE/INSERT/DELETE: Dictionary with "rows_affected" count
    
#     Safety: Only SELECT queries are allowed without confirm=True to prevent accidental data changes.
#     """
#     return _execute_sql(query, params, confirm)


# def arbitrary_update(query: str, params: Optional[Dict[str, Any]] = None):
#     """Execute UPDATE, INSERT, or DELETE SQL statements with automatic confirmation.
    
#     This is a convenience function that automatically sets confirm=True for database modifications.
#     Use when you need to modify data without explicitly passing confirm=True to run_sql.
    
#     Parameters:
#     - query (str): SQL UPDATE, INSERT, or DELETE statement. Use %(param_name)s for parameters
#     - params (dict, optional): Dictionary of named parameters for the query
    
#     Examples:
#     - arbitrary_update("UPDATE planned_sets SET load = %(new_load)s WHERE id = %(set_id)s", 
#                        {"new_load": 185, "set_id": 1})
#     - arbitrary_update("INSERT INTO exercises (name) VALUES (%(exercise_name)s)", 
#                        {"exercise_name": "overhead press"})
#     - arbitrary_update("DELETE FROM planned_sets WHERE order_num > %(max_order)s", 
#                        {"max_order": 10})
    
#     Returns: Dictionary with "rows_affected" count showing how many rows were modified
    
#     Note: This function is for advanced use cases. Most operations should use the specific 
#     functions like new_daily_plan, complete_planned_set, etc.
#     """
#     if params is None:
#         params = {}
#     return _execute_sql(query, params=params, confirm=True)


def set_timer(minutes: int):
    """Set a workout timer for rest periods or workout duration.
    
    Useful for timing rest between sets or entire workout duration.
    Timer runs in the background and can be checked with get_timer().
    
    Parameters:
    - minutes (int): Timer duration in minutes (1-180). Max 3 hours
    
    Examples:
    - set_timer(3)   # 3-minute rest timer
    - set_timer(90)  # 90-minute workout timer
    - set_timer(2)   # 2-minute rest between sets
    
    Returns: Success message with timer duration or error message
    
    Note: Setting a new timer will replace any existing timer.
    """
    if not (1 <= minutes <= 180):  # Max 3 hours
        raise ValueError("Timer duration must be between 1 and 180 minutes")
    
    try:
        import subprocess
        import os
        # Ensure we're in the correct directory for the timer script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        timer_script = os.path.join(script_dir, 'timer_temp.py')
        result = subprocess.run(['python', timer_script, 'set', str(minutes)], 
                               capture_output=True, text=True, cwd=script_dir)
        if result.returncode == 0:
            return f"Timer set for {minutes} minutes"
        else:
            return f"Timer error: {result.stderr.strip()}"
    except Exception as e:
        return f"Timer error: {e}"


def get_timer() -> Dict[str, Any]:
    """Check the current timer status and remaining time.
    
    Use this to see how much time is left on a rest timer or workout timer.
    
    No parameters required.
    
    Returns: Dictionary containing:
    - status (str): Timer state - "running", "expired", "no_timer", or "error"  
    - remaining_seconds (int): Seconds left (if status is "running")
    - message (str): Human-readable status message
    
    Possible statuses:
    - "running": Timer is active with remaining_seconds showing time left
    - "expired": Timer has finished - time to get back to work!
    - "no_timer": No timer is currently set
    - "error": Problem checking timer status
    
    Examples:
    - get_timer() might return {"status": "running", "remaining_seconds": 120, "message": "2:00 remaining"}
    - get_timer() might return {"status": "expired", "message": "Timer expired!"}
    - get_timer() might return {"status": "no_timer", "message": "No timer set"}
    
    Use this between sets to check if rest time is up.
    """
    try:
        import subprocess
        import os
        import json
        # Ensure we're in the correct directory for the timer script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        timer_script = os.path.join(script_dir, 'timer_temp.py')
        result = subprocess.run(['python', timer_script, 'get'], 
                               capture_output=True, text=True, cwd=script_dir)
        if result.returncode == 0:
            try:
                # Parse the JSON output from timer_temp.py
                timer_data = json.loads(result.stdout.strip())
                return timer_data
            except json.JSONDecodeError:
                # If it's not JSON, treat it as a simple message
                return {"status": "no_timer", "message": result.stdout.strip()}
        else:
            return {"status": "error", "message": f"Timer error: {result.stderr.strip()}"}
    except Exception as e:
        return {"status": "error", "message": f"Timer error: {e}"}


__all__ = [
    "new_daily_plan",
    "get_today_plan",
    "log_completed_set",
    "complete_planned_set",
    "update_summary",
    "get_recent_history",
    "set_weekly_split_day",
    "get_weekly_split",
    # "run_sql",
    # "arbitrary_update",
    "set_timer",
    "get_timer",
]
