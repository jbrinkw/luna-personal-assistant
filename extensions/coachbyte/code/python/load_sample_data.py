#!/usr/bin/env python3
"""
Load comprehensive sample data into PostgreSQL database.
This creates 3 days of MMA-focused workout data (current day, current day - 1, current day - 2).
"""

import uuid
import time
import errno
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date, timedelta
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))
import db_config

# Guard & cooldown configuration
GUARD_PATH = os.environ.get("COACHBYTE_DB_RESET_GUARD", "/tmp/coachbyte_db_reset.guard")
TS_PATH = os.environ.get("COACHBYTE_DB_RESET_TS", "/tmp/coachbyte_db_reset.ts")
COOLDOWN_S = int(os.environ.get("COACHBYTE_DB_RESET_COOLDOWN_S", "60"))


def _acquire_guard() -> int | None:
    """Try to create an exclusive guard file. Return fd if acquired, else None."""
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        fd = os.open(GUARD_PATH, flags, 0o644)
        return fd
    except FileExistsError:
        return None
    except OSError as e:
        if e.errno == errno.EEXIST:
            return None
        raise


def _release_guard(fd: int | None) -> None:
    try:
        if fd is not None:
            try:
                os.close(fd)
            except Exception:
                pass
        if os.path.exists(GUARD_PATH):
            os.unlink(GUARD_PATH)
    except Exception:
        pass


def _cooldown_active() -> bool:
    try:
        if not os.path.exists(TS_PATH):
            return False
        with open(TS_PATH, "r") as f:
            raw = f.read().strip()
        last = float(raw) if raw else 0.0
        return (time.time() - last) < COOLDOWN_S
    except Exception:
        return False


def _update_timestamp() -> None:
    try:
        with open(TS_PATH, "w") as f:
            f.write(str(int(time.time())))
    except Exception:
        pass


def generate_uuid():
    """Generate a UUID string"""
    return str(uuid.uuid4())


def get_connection():
    """Get PostgreSQL connection"""
    config = db_config.get_db_config()
    return psycopg2.connect(
        host=config['host'],
        port=config['port'],
        database=config['database'],
        user=config['user'],
        password=config['password']
    )


def load_comprehensive_sample_data():
    """Load comprehensive 3-day MMA workout sample data with dynamic dates"""
    print("Loading comprehensive 3-day MMA workout sample data...")
    
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Create schema (in case it doesn't exist)
        print("Creating schema...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS exercises (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL
            );
            CREATE TABLE IF NOT EXISTS daily_logs (
                id TEXT PRIMARY KEY,
                log_date DATE NOT NULL UNIQUE,
                summary TEXT
            );
            CREATE TABLE IF NOT EXISTS planned_sets (
                id SERIAL PRIMARY KEY,
                log_id TEXT REFERENCES daily_logs(id) ON DELETE CASCADE,
                exercise_id INTEGER REFERENCES exercises(id),
                order_num INTEGER NOT NULL,
                reps INTEGER NOT NULL,
                load REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS completed_sets (
                id SERIAL PRIMARY KEY,
                log_id TEXT REFERENCES daily_logs(id) ON DELETE CASCADE,
                exercise_id INTEGER REFERENCES exercises(id),
                reps_done INTEGER,
                load_done REAL,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS split_sets (
                id SERIAL PRIMARY KEY,
                day_of_week INTEGER NOT NULL,
                exercise_id INTEGER REFERENCES exercises(id),
                order_num INTEGER NOT NULL,
                reps INTEGER NOT NULL,
                load REAL NOT NULL,
                rest INTEGER DEFAULT 60,
                relative BOOLEAN DEFAULT FALSE
            );
            CREATE INDEX IF NOT EXISTS ix_split_order ON split_sets (day_of_week, order_num);
            CREATE TABLE IF NOT EXISTS timer (
                id SERIAL PRIMARY KEY,
                timer_end_time TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Clear existing data
        print("Clearing existing data...")
        cur.execute("DELETE FROM completed_sets")
        cur.execute("DELETE FROM planned_sets")
        cur.execute("DELETE FROM split_sets")
        cur.execute("DELETE FROM daily_logs")
        cur.execute("DELETE FROM exercises")
        cur.execute("DELETE FROM timer")
        
        # Create dates: current day, current day - 1, current day - 2
        today = date.today()
        dates = [today - timedelta(days=i) for i in range(3)]  # [today, yesterday, day before yesterday]
        dates.reverse()  # [day before yesterday, yesterday, today]
        
        # Create daily logs
        log_ids = []
        summaries = [
            "Solid upper body session. Push-ups felt strong, pull-ups getting easier. Bench press moved well at 135. Ready for legs tomorrow.",
            "Tough leg day. Squats felt heavy but good form. Deadlifts strong for first 2 sets, skipped last set due to form breakdown. Conditioning work tomorrow.",
            ""  # Today - no summary yet
        ]
        
        for i, workout_date in enumerate(dates):
            log_id = generate_uuid()
            log_ids.append(log_id)
            cur.execute(
                "INSERT INTO daily_logs (id, log_date, summary) VALUES (%s, %s, %s)",
                (log_id, workout_date.isoformat(), summaries[i])
            )
            print(f"Created daily log for {workout_date.isoformat()}")
        
        # Create exercises
        exercises = [
            "push-ups", "pull-ups", "bench press", "overhead press", "rows", "dips",
            "squats", "deadlifts", "bodyweight squats", "walking lunges", "calf raises", "plank",
            "burpees", "mountain climbers"
        ]
        
        exercise_ids = {}
        for exercise in exercises:
            cur.execute("INSERT INTO exercises (name) VALUES (%s) RETURNING id", (exercise,))
            result = cur.fetchone()
            if result:
                exercise_ids[exercise] = result['id']
                print(f"Added exercise: {exercise} (ID: {result['id']})")
            else:
                raise Exception(f"Failed to insert exercise: {exercise}")

        # Weekly split - one entry per day
        day_map = {
            "sunday": 0,
            "monday": 1,
            "tuesday": 2,
            "wednesday": 3,
            "thursday": 4,
            "friday": 5,
            "saturday": 6,
        }
        weekly_split = [
            ("sunday", "push-ups", 10, 0),
            ("monday", "bench press", 5, 135),
            ("tuesday", "squats", 8, 185),
            ("wednesday", "deadlifts", 5, 225),
            ("thursday", "overhead press", 8, 95),
            ("friday", "rows", 10, 115),
            ("saturday", "dips", 12, 0),
        ]
        for day_name, exercise, reps, load in weekly_split:
            day_num = day_map[day_name]
            ex_id = exercise_ids[exercise]
            cur.execute(
                "INSERT INTO split_sets (day_of_week, exercise_id, order_num, reps, load, rest, relative) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (day_num, ex_id, 1, reps, load, 60, False),
            )

        # Day 1 (2 days ago) - Upper Body Focus
        day1_planned = [
            ("push-ups", 1, 15, 0),
            ("push-ups", 2, 15, 0),
            ("push-ups", 3, 15, 0),
            ("pull-ups", 4, 8, 0),
            ("pull-ups", 5, 8, 0),
            ("pull-ups", 6, 8, 0),
            ("bench press", 7, 10, 135),
            ("bench press", 8, 10, 135),
            ("bench press", 9, 10, 135),
            ("overhead press", 10, 8, 95),
            ("overhead press", 11, 8, 95),
            ("overhead press", 12, 8, 95),
            ("rows", 13, 12, 115),
            ("rows", 14, 12, 115),
            ("rows", 15, 12, 115),
            ("dips", 16, 12, 0),
            ("dips", 17, 12, 0),
        ]
        
        day1_completed = [
            ("push-ups", 15, 0),
            ("push-ups", 15, 0),
            ("push-ups", 15, 0),
            ("pull-ups", 8, 0),
            ("pull-ups", 8, 0),
            ("pull-ups", 8, 0),
            ("bench press", 10, 135),
            ("bench press", 10, 135),
            ("bench press", 10, 135),
            ("overhead press", 8, 95),
            ("overhead press", 8, 95),
            ("overhead press", 8, 95),
            ("rows", 12, 115),
            ("rows", 12, 115),
            ("rows", 12, 115),
            ("dips", 12, 0),
            ("dips", 12, 0),
        ]
        
        # Day 2 (yesterday) - Lower Body Focus
        day2_planned = [
            ("squats", 1, 12, 185),
            ("squats", 2, 12, 185),
            ("squats", 3, 12, 185),
            ("squats", 4, 12, 185),
            ("deadlifts", 5, 8, 225),
            ("deadlifts", 6, 8, 225),
            ("deadlifts", 7, 8, 225),
            ("bodyweight squats", 8, 20, 0),
            ("bodyweight squats", 9, 20, 0),
            ("walking lunges", 10, 16, 0),
            ("walking lunges", 11, 16, 0),
            ("walking lunges", 12, 16, 0),
            ("calf raises", 13, 15, 45),
            ("calf raises", 14, 15, 45),
            ("calf raises", 15, 15, 45),
            ("plank", 16, 45, 0),
            ("plank", 17, 45, 0),
            ("plank", 18, 45, 0),
        ]
        
        day2_completed = [
            ("squats", 12, 185),
            ("squats", 12, 185),
            ("squats", 12, 185),
            ("squats", 12, 185),
            ("deadlifts", 8, 225),
            ("deadlifts", 8, 225),
            # Third deadlift set skipped
            ("bodyweight squats", 20, 0),
            ("bodyweight squats", 20, 0),
            ("walking lunges", 16, 0),
            ("walking lunges", 16, 0),
            ("walking lunges", 16, 0),
            ("calf raises", 15, 45),
            ("calf raises", 15, 45),
            ("calf raises", 15, 45),
            ("plank", 45, 0),
            ("plank", 45, 0),
            ("plank", 45, 0),
        ]
        
        # Day 3 (today) - Full Body/Conditioning
        day3_planned = [
            ("burpees", 1, 10, 0),
            ("burpees", 2, 10, 0),
            ("burpees", 3, 10, 0),
            ("burpees", 4, 10, 0),
            ("push-ups", 5, 12, 0),
            ("push-ups", 6, 12, 0),
            ("push-ups", 7, 12, 0),
            ("pull-ups", 8, 6, 0),
            ("pull-ups", 9, 6, 0),
            ("pull-ups", 10, 6, 0),
            ("bodyweight squats", 11, 15, 0),
            ("bodyweight squats", 12, 15, 0),
            ("bodyweight squats", 13, 15, 0),
            ("mountain climbers", 14, 20, 0),
            ("mountain climbers", 15, 20, 0),
            ("mountain climbers", 16, 20, 0),
            ("plank", 17, 60, 0),
            ("plank", 18, 60, 0),
            ("plank", 19, 60, 0),
        ]
        
        day3_completed = [
            ("burpees", 10, 0),
            ("burpees", 10, 0),
            ("push-ups", 12, 0),
            ("pull-ups", 6, 0),
            ("bodyweight squats", 15, 0),
            ("mountain climbers", 20, 0),
            ("plank", 60, 0),
        ]
        
        # Insert planned sets
        all_planned = [(day1_planned, log_ids[0]), (day2_planned, log_ids[1]), (day3_planned, log_ids[2])]
        total_planned = 0
        for day_data, log_id in all_planned:
            for exercise, order_num, reps, load in day_data:
                exercise_id = exercise_ids[exercise]
                cur.execute(
                    "INSERT INTO planned_sets (log_id, exercise_id, order_num, reps, load) VALUES (%s, %s, %s, %s, %s)",
                    (log_id, exercise_id, order_num, reps, load)
                )
                total_planned += 1
        
        # Insert completed sets
        all_completed = [(day1_completed, log_ids[0]), (day2_completed, log_ids[1]), (day3_completed, log_ids[2])]
        total_completed = 0
        for day_data, log_id in all_completed:
            for exercise, reps, load in day_data:
                exercise_id = exercise_ids[exercise]
                cur.execute(
                    "INSERT INTO completed_sets (log_id, exercise_id, reps_done, load_done) VALUES (%s, %s, %s, %s)",
                    (log_id, exercise_id, reps, load)
                )
                total_completed += 1
        
        # Commit all changes
        conn.commit()
        
        print("\nComprehensive sample data loaded successfully!")
        print("Database contains:")
        print(f"- {len(exercises)} exercises")
        print(f"- {total_planned} planned sets across 3 workouts")
        print(f"- {total_completed} completed sets")
        print(f"- 3 daily logs ({dates[0].isoformat()}, {dates[1].isoformat()}, {dates[2].isoformat()})")
        print(f"- Day 1 ({dates[0].isoformat()}): Upper body focus - 17 planned, 17 completed")
        print(f"- Day 2 ({dates[1].isoformat()}): Lower body focus - 18 planned, 17 completed")
        print(f"- Day 3 ({dates[2].isoformat()}): Full body conditioning - 19 planned, 7 completed")
        
    except Exception as e:
        print(f"Error loading sample data: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    fd = _acquire_guard()
    if fd is None:
        # Another process is managing the reset (or a very recent reset occurred). Skip.
        print("DB reset skipped: guard present (another process or recent reset).")
        sys.exit(0)
    try:
        if _cooldown_active():
            print(f"DB reset skipped: cooldown active (< {COOLDOWN_S}s).")
            sys.exit(0)
        # Perform reset
        load_comprehensive_sample_data()
        _update_timestamp()
    except Exception as error:
        print(f"Error loading sample data: {error}")
        raise
    finally:
        _release_guard(fd)
