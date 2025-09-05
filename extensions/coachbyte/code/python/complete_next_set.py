import sys
import json
import os

# Ensure we can import tools from project root
sys.path.append(os.path.dirname(__file__))

# Import the actual function, not the tool wrapper
from typing import Optional
from datetime import datetime, timezone
from db import get_connection, get_today_log_id
import psycopg2.extras

def complete_planned_set(exercise: Optional[str] = None, reps: Optional[int] = None, load: Optional[float] = None):
    """Complete the next planned set in the workout queue, with optional overrides."""
    MAX_LOAD = 2000
    MAX_REPS = 100
    
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        log_id = get_today_log_id(conn)
        
        # Find the next uncompleted planned set
        if exercise:
            # Complete specific exercise - find first uncompleted planned set for that exercise
            cur.execute("""
                SELECT ps.id, ps.exercise_id, e.name as exercise, ps.reps, ps.load, ps.rest, ps.order_num
                FROM planned_sets ps
                JOIN exercises e ON ps.exercise_id = e.id
                LEFT JOIN completed_sets cs ON ps.id = cs.planned_set_id
                WHERE ps.log_id = %s AND e.name = %s AND cs.id IS NULL
                ORDER BY ps.order_num
                LIMIT 1
            """, (log_id, exercise))
        else:
            # Complete next uncompleted planned set in order
            cur.execute("""
                SELECT ps.id, ps.exercise_id, e.name as exercise, ps.reps, ps.load, ps.rest, ps.order_num
                FROM planned_sets ps
                JOIN exercises e ON ps.exercise_id = e.id
                LEFT JOIN completed_sets cs ON ps.id = cs.planned_set_id
                WHERE ps.log_id = %s AND cs.id IS NULL
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
        
        # Record the completion
        cur.execute(
            "INSERT INTO completed_sets (log_id, exercise_id, planned_set_id, reps_done, load_done, completed_at) VALUES (%s, %s, %s, %s, %s, %s)",
            (log_id, planned_set['exercise_id'], planned_set['id'], actual_reps, actual_load, datetime.now(timezone.utc)),
        )
        
        # Don't delete the planned set - just mark it as completed by linking it
        # This preserves the original plan structure while tracking completion
        
        conn.commit()
        
        # Set timer for rest period if there's a rest time (write to DB so UI can read it)
        rest_time = int(planned_set.get('rest', 60) or 0)
        if rest_time > 0:
            try:
                # Replace any existing timer and set new end time in seconds from now
                cur.execute('DELETE FROM timer')
                cur.execute(
                    """
                    INSERT INTO timer (timer_end_time)
                    VALUES (CURRENT_TIMESTAMP + (%s || ' seconds')::interval)
                    """,
                    (str(rest_time),)
                )
                conn.commit()
                rest_info = f" Rest timer set for {rest_time} seconds."
            except Exception as e:
                # Do not fail the main operation on timer error
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


def main():
    try:
        result = complete_planned_set()
        print(json.dumps({"message": result}))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
