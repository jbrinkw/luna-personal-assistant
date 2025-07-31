"""Database helper functions for PostgreSQL backend."""

import os
import psycopg2
import psycopg2.extras
import uuid
from datetime import datetime, date, timedelta, timezone

# Database configuration
from db_config import get_db_config

# Connection helper
def get_connection():
    config = get_db_config()
    conn = psycopg2.connect(**config)
    conn.autocommit = False
    return conn

# Initialize database with schema
SCHEMA = """
DROP TABLE IF EXISTS completed_sets CASCADE;
DROP TABLE IF EXISTS planned_sets CASCADE;
DROP TABLE IF EXISTS daily_logs CASCADE;
DROP TABLE IF EXISTS exercises CASCADE;
DROP TABLE IF EXISTS timer CASCADE;
DROP TABLE IF EXISTS chat_messages CASCADE;

CREATE TABLE tracked_prs (
    exercise VARCHAR(255) NOT NULL,
    reps INTEGER NOT NULL,
    max_load REAL NOT NULL,
    PRIMARY KEY (exercise, reps)
);

CREATE TABLE tracked_exercises (
    exercise VARCHAR(255) PRIMARY KEY
);

CREATE TABLE split_sets (
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

CREATE TABLE exercises (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL
);

CREATE TABLE daily_logs (
    id TEXT PRIMARY KEY,
    log_date DATE NOT NULL UNIQUE,
    summary TEXT
);

CREATE TABLE planned_sets (
    id SERIAL PRIMARY KEY,
    log_id TEXT REFERENCES daily_logs(id) ON DELETE CASCADE,
    exercise_id INTEGER REFERENCES exercises(id),
    order_num INTEGER NOT NULL,
    reps INTEGER NOT NULL,
    load REAL NOT NULL,
    rest INTEGER DEFAULT 60
);
CREATE INDEX IF NOT EXISTS ix_planned_order ON planned_sets (log_id, order_num);

CREATE TABLE completed_sets (
    id SERIAL PRIMARY KEY,
    log_id TEXT REFERENCES daily_logs(id) ON DELETE CASCADE,
    exercise_id INTEGER REFERENCES exercises(id),
    planned_set_id INTEGER REFERENCES planned_sets(id),
    reps_done INTEGER,
    load_done REAL,
    completed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_completed_time ON completed_sets (log_id, completed_at);

CREATE TABLE timer (
    id SERIAL PRIMARY KEY,
    timer_end_time TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    message_type VARCHAR(10) NOT NULL CHECK (message_type IN ('user', 'assistant')),
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_chat_timestamp ON chat_messages (timestamp DESC);
"""


def init_db(sample: bool = False):
    """Create a new database schema. If sample=True, populate with demo data."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        # Execute schema (drops and recreates tables)
        cur.execute(SCHEMA)
        
        # Initialize with default tracked exercises
        cur.execute("""
            INSERT INTO tracked_exercises (exercise) VALUES 
            ('Bench Press'), ('Squat'), ('Deadlift')
        """)
        
        if sample:
            populate_comprehensive_sample_data(conn)
        conn.commit()
    finally:
        conn.close()


def populate_comprehensive_sample_data(conn):
    """Create comprehensive 3-day MMA-focused workout data with dynamic dates"""
    
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
    
    cur = conn.cursor()
    for i, workout_date in enumerate(dates):
        log_id = str(uuid.uuid4())
        log_ids.append(log_id)
        cur.execute(
            "INSERT INTO daily_logs (id, log_date, summary) VALUES (%s, %s, %s)",
            (log_id, workout_date.isoformat(), summaries[i])
        )
    
    # Create exercises
    exercises = [
        "push-ups", "pull-ups", "bench press", "overhead press", "rows", "dips",
        "squats", "deadlifts", "bodyweight squats", "walking lunges", "calf raises", "plank",
        "burpees", "mountain climbers"
    ]
    
    exercise_ids = {}
    for exercise in exercises:
        cur.execute("INSERT INTO exercises (name) VALUES (%s) RETURNING id", (exercise,))
        exercise_ids[exercise] = cur.fetchone()[0]
    
    # Day 1 (2 days ago) - Upper Body Focus
    day1_planned = [
        ("push-ups", 1, 15, 0, 60),
        ("push-ups", 2, 15, 0, 60),
        ("push-ups", 3, 15, 0, 90),
        ("pull-ups", 4, 8, 0, 90),
        ("pull-ups", 5, 8, 0, 90),
        ("pull-ups", 6, 8, 0, 120),
        ("bench press", 7, 10, 135, 120),
        ("bench press", 8, 10, 135, 120),
        ("bench press", 9, 10, 135, 180),
        ("overhead press", 10, 8, 95, 90),
        ("overhead press", 11, 8, 95, 90),
        ("overhead press", 12, 8, 95, 120),
        ("rows", 13, 12, 115, 90),
        ("rows", 14, 12, 115, 90),
        ("rows", 15, 12, 115, 120),
        ("dips", 16, 12, 0, 60),
        ("dips", 17, 12, 0, 60),
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
        ("squats", 1, 12, 185, 180),
        ("squats", 2, 12, 185, 180),
        ("squats", 3, 12, 185, 180),
        ("squats", 4, 12, 185, 240),
        ("deadlifts", 5, 8, 225, 240),
        ("deadlifts", 6, 8, 225, 240),
        ("deadlifts", 7, 8, 225, 300),
        ("bodyweight squats", 8, 20, 0, 60),
        ("bodyweight squats", 9, 20, 0, 60),
        ("walking lunges", 10, 16, 0, 60),
        ("walking lunges", 11, 16, 0, 60),
        ("walking lunges", 12, 16, 0, 90),
        ("calf raises", 13, 15, 45, 45),
        ("calf raises", 14, 15, 45, 45),
        ("calf raises", 15, 15, 45, 60),
        ("plank", 16, 45, 0, 60),
        ("plank", 17, 45, 0, 60),
        ("plank", 18, 45, 0, 60),
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
        ("burpees", 1, 10, 0, 90),
        ("burpees", 2, 10, 0, 90),
        ("burpees", 3, 10, 0, 90),
        ("burpees", 4, 10, 0, 120),
        ("push-ups", 5, 12, 0, 60),
        ("push-ups", 6, 12, 0, 60),
        ("push-ups", 7, 12, 0, 90),
        ("pull-ups", 8, 6, 0, 90),
        ("pull-ups", 9, 6, 0, 90),
        ("pull-ups", 10, 6, 0, 120),
        ("bodyweight squats", 11, 15, 0, 45),
        ("bodyweight squats", 12, 15, 0, 45),
        ("bodyweight squats", 13, 15, 0, 60),
        ("mountain climbers", 14, 20, 0, 30),
        ("mountain climbers", 15, 20, 0, 30),
        ("mountain climbers", 16, 20, 0, 60),
        ("plank", 17, 60, 0, 60),
        ("plank", 18, 60, 0, 60),
        ("plank", 19, 60, 0, 60),
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
    
    # Insert planned sets and keep mapping of inserted IDs by exercise
    all_planned = [(day1_planned, log_ids[0]), (day2_planned, log_ids[1]), (day3_planned, log_ids[2])]
    planned_map = {}
    for day_data, log_id in all_planned:
        planned_map[log_id] = {}
        for exercise, order_num, reps, load, rest in day_data:
            exercise_id = exercise_ids[exercise]
            cur.execute(
                "INSERT INTO planned_sets (log_id, exercise_id, order_num, reps, load, rest) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                (log_id, exercise_id, order_num, reps, load, rest)
            )
            ps_id = cur.fetchone()[0]
            planned_map[log_id].setdefault(exercise, []).append(ps_id)
    
    # Insert completed sets
    all_completed = [(day1_completed, log_ids[0]), (day2_completed, log_ids[1]), (day3_completed, log_ids[2])]
    for day_data, log_id in all_completed:
        for exercise, reps, load in day_data:
            exercise_id = exercise_ids[exercise]
            ps_id = None
            if planned_map.get(log_id) and planned_map[log_id].get(exercise):
                ps_id = planned_map[log_id][exercise].pop(0)
            cur.execute(
                "INSERT INTO completed_sets (log_id, exercise_id, planned_set_id, reps_done, load_done, completed_at) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)",
                (log_id, exercise_id, ps_id, reps, load)
            )


def populate_sample_data(conn):
    """Legacy function - kept for compatibility"""
    return populate_comprehensive_sample_data(conn)


def get_today_log_id(conn):
    today = date.today().isoformat()
    cur = conn.cursor()
    cur.execute("SELECT id FROM daily_logs WHERE log_date = %s", (today,))
    row = cur.fetchone()
    if row:
        return row[0]
    log_id = str(uuid.uuid4())
    cur.execute("INSERT INTO daily_logs (id, log_date) VALUES (%s, %s)", (log_id, today))
    conn.commit()
    return log_id

def save_chat_message(message_type, content):
    """Save a chat message to the database and keep only the last 25 messages"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        
        # Insert the new message
        cur.execute(
            "INSERT INTO chat_messages (message_type, content) VALUES (%s, %s)",
            (message_type, content)
        )
        
        # Keep only the last 25 messages
        cur.execute("""
            DELETE FROM chat_messages 
            WHERE id NOT IN (
                SELECT id FROM chat_messages 
                ORDER BY timestamp DESC 
                LIMIT 25
            )
        """)
        
        conn.commit()
    finally:
        conn.close()

def get_recent_chat_messages(limit=25):
    """Get the most recent chat messages, ordered chronologically"""
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("""
            SELECT message_type, content, timestamp 
            FROM chat_messages 
            ORDER BY timestamp ASC 
            LIMIT %s
        """, (limit,))
        
        messages = []
        for row in cur.fetchall():
            messages.append({
                'type': row['message_type'],
                'content': row['content'],
                'timestamp': row['timestamp'].isoformat()
            })
        
        return messages
    finally:
        conn.close()

def clear_chat_memory():
    """Clear all chat messages from the database"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM chat_messages")
        conn.commit()
    finally:
        conn.close()

def apply_migrations():
    """Apply incremental schema changes."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        # Add planned_set_id column to completed_sets if it does not exist
        cur.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name='completed_sets' AND column_name='planned_set_id'
            """
        )
        if not cur.fetchone():
            cur.execute(
                "ALTER TABLE completed_sets ADD COLUMN planned_set_id INTEGER REFERENCES planned_sets(id)"
            )
        conn.commit()
    finally:
        conn.close()

def get_tracked_exercises():
    """Get all tracked exercises from the database"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT exercise FROM tracked_exercises ORDER BY exercise")
        return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()

def add_tracked_exercise(exercise_name):
    """Add a new tracked exercise"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO tracked_exercises (exercise) VALUES (%s)", (exercise_name,))
        conn.commit()
    finally:
        conn.close()

def remove_tracked_exercise(exercise_name):
    """Remove a tracked exercise"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM tracked_exercises WHERE exercise = %s", (exercise_name,))
        conn.commit()
    finally:
        conn.close()

def get_current_prs():
    """Get current PRs for all tracked exercises"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        
        # Get all tracked exercises
        tracked_exercises = get_tracked_exercises()
        
        if not tracked_exercises:
            return []
        
        # Build query for all tracked exercises
        placeholders = ','.join(['%s'] * len(tracked_exercises))
        
        cur.execute(f"""
            SELECT 
                e.name as exercise,
                cs.reps_done as reps,
                MAX(cs.load_done) as max_load
            FROM completed_sets cs
            JOIN exercises e ON cs.exercise_id = e.id
            WHERE e.name IN ({placeholders})
            AND cs.reps_done IS NOT NULL 
            AND cs.load_done IS NOT NULL
            GROUP BY e.name, cs.reps_done
            ORDER BY e.name, cs.reps_done
        """, tracked_exercises)
        
        return [{'exercise': row[0], 'reps': row[1], 'max_load': row[2]} for row in cur.fetchall()]
    finally:
        conn.close()

if __name__ == "__main__":
    print("Resetting database with new schema...")
    init_db(sample=False)
    apply_migrations()
    print("Database reset complete with sample data!")
