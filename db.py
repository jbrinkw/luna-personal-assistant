import os
import sqlite3
import uuid
from datetime import datetime, date

# Database configuration
DB_PATH = os.environ.get("WORKOUT_DB", "workout.db")

# Connection helper
def get_connection():
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize database schema
SCHEMA = """
CREATE TABLE IF NOT EXISTS exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_logs (
    id TEXT PRIMARY KEY,
    log_date DATE NOT NULL UNIQUE,
    summary TEXT
);

CREATE TABLE IF NOT EXISTS planned_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_id TEXT REFERENCES daily_logs(id) ON DELETE CASCADE,
    exercise_id INTEGER REFERENCES exercises(id),
    order_num INTEGER NOT NULL,
    reps INTEGER NOT NULL,
    load REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_planned_order ON planned_sets (log_id, order_num);

CREATE TABLE IF NOT EXISTS completed_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_id TEXT REFERENCES daily_logs(id) ON DELETE CASCADE,
    exercise_id INTEGER REFERENCES exercises(id),
    reps_done INTEGER,
    load_done REAL,
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_completed_time ON completed_sets (log_id, completed_at);
"""


def init_db(sample: bool = False):
    """Create a new database. If sample=True, populate with demo data."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = get_connection()
    conn.executescript(SCHEMA)
    if sample:
        populate_sample_data(conn)
    conn.commit()
    conn.close()


def populate_sample_data(conn: sqlite3.Connection):
    today = date.today().isoformat()
    log_id = str(uuid.uuid4())
    conn.execute("INSERT INTO daily_logs (id, log_date, summary) VALUES (?, ?, '')", (log_id, today))

    def add_ex(name):
        cur = conn.execute("INSERT INTO exercises (name) VALUES (?) RETURNING id", (name,))
        return cur.fetchone()[0]

    bench = add_ex("bench press")
    squat = add_ex("squat")
    deadlift = add_ex("deadlift")

    planned = [
        (bench, 1, 10, 45),
        (bench, 2, 8, 65),
        (bench, 3, 5, 85),
        (squat, 4, 10, 95),
        (squat, 5, 8, 135),
        (squat, 6, 5, 185),
        (deadlift, 7, 5, 135),
        (deadlift, 8, 5, 185),
        (deadlift, 9, 3, 225),
    ]
    for ex_id, order_num, reps, load in planned:
        conn.execute(
            "INSERT INTO planned_sets (log_id, exercise_id, order_num, reps, load) VALUES (?, ?, ?, ?, ?)",
            (log_id, ex_id, order_num, reps, load),
        )

    completed = [
        (bench, 1, 10, 45),
        (bench, 2, 8, 65),
        (squat, 4, 10, 95),
        (deadlift, 7, 5, 135),
    ]
    for ex_id, order_num, reps, load in completed:
        conn.execute(
            "INSERT INTO completed_sets (log_id, exercise_id, reps_done, load_done, completed_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
            (log_id, ex_id, reps, load),
        )


def get_today_log_id(conn):
    today = date.today().isoformat()
    cur = conn.execute("SELECT id FROM daily_logs WHERE log_date = ?", (today,))
    row = cur.fetchone()
    if row:
        return row[0]
    log_id = str(uuid.uuid4())
    conn.execute("INSERT INTO daily_logs (id, log_date) VALUES (?, ?)", (log_id, today))
    conn.commit()
    return log_id


