# PostgreSQL Migration Guide

This document outlines the migration from SQLite to PostgreSQL for the Luna Langflow workout tracker.

## 🔄 What Changed

### Database Backend
- **Before**: SQLite (`workout.db` file)
- **After**: PostgreSQL server at `192.168.1.93:5432`

### Key Files Modified
- `db.py` - Complete rewrite for PostgreSQL
- `tools.py` - Updated queries and connection handling
- `requirements.txt` - Already included `psycopg2-binary`

### New Files Added
- `db_config.py` - Configuration helper
- `test_postgres_connection.py` - Connection testing
- `README_POSTGRES.md` - This documentation

## 🛠️ Setup Instructions

### 1. PostgreSQL Server Setup
Ensure PostgreSQL is running on `192.168.1.93:5432` with:
- Database: `workout_tracker`
- User: `postgres` (or custom user)
- Proper network access configured

### 2. Environment Configuration
Set environment variables for database connection:

```bash
export DB_HOST=192.168.1.93
export DB_PORT=5432
export DB_NAME=workout_tracker
export DB_USER=postgres
export DB_PASSWORD=your_password_here
```

Or create a `.env` file:
```
DB_HOST=192.168.1.93
DB_PORT=5432
DB_NAME=workout_tracker
DB_USER=postgres
DB_PASSWORD=your_password_here
```

### 3. Test Connection
Run the connection test before using the system:

```bash
python test_postgres_connection.py
```

This will verify:
- ✅ Database connection
- ✅ Schema creation
- ✅ Sample data population
- ✅ Basic queries

### 4. Initialize Database
Initialize with sample data:

```python
python -c "import db; db.init_db(sample=True)"
```

## 🏃‍♂️ Running the System

All existing scripts work the same way:

```bash
# Run comprehensive tests
python test_comprehensive.py

# Run basic agent tests
python test_agent.py

# Start demo chat
python demo_chat.py
```

## 🔧 Configuration Details

### Database Schema
```sql
-- PostgreSQL schema (auto-created)
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
    load REAL NOT NULL
);

CREATE TABLE completed_sets (
    id SERIAL PRIMARY KEY,
    log_id TEXT REFERENCES daily_logs(id) ON DELETE CASCADE,
    exercise_id INTEGER REFERENCES exercises(id),
    reps_done INTEGER,
    load_done REAL,
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Key Differences from SQLite
- `SERIAL` instead of `INTEGER PRIMARY KEY AUTOINCREMENT`
- `%s` parameter substitution instead of `?`
- `psycopg2.extras.RealDictCursor` for dict-like rows
- `RETURNING` clause for getting inserted IDs
- Network connection instead of file-based

## 🛡️ Benefits of PostgreSQL

1. **Scalability**: Multi-user support, better performance
2. **Reliability**: ACID compliance, robust data integrity
3. **Features**: Advanced SQL features, JSON support
4. **Deployment**: Centralized database for multiple clients
5. **Monitoring**: Better logging and monitoring capabilities

## 🔍 Troubleshooting

### Connection Issues
```bash
# Test configuration
python db_config.py

# Check PostgreSQL service
sudo systemctl status postgresql  # On server

# Check network connectivity
ping 192.168.1.93
telnet 192.168.1.93 5432
```

### Permission Issues
```sql
-- Grant permissions (run on PostgreSQL server)
GRANT ALL PRIVILEGES ON DATABASE workout_tracker TO your_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_user;
```

### Firewall Issues
```bash
# Allow PostgreSQL port (on server)
sudo ufw allow 5432
# Or for specific IP
sudo ufw allow from 192.168.1.0/24 to any port 5432
```

## 📊 Sample Data

The system includes comprehensive 3-day MMA workout data:
- **14 exercises** (bodyweight + weighted)
- **3 daily logs** (current day and 2 previous days)
- **54 planned sets** across 3 workouts
- **Realistic completion data** with some missed sets

Run `python test_postgres_connection.py` to verify sample data creation.

## 🔄 Migration from SQLite

If you have existing SQLite data, you can migrate it:

1. Export SQLite data to SQL
2. Adjust schema differences
3. Import to PostgreSQL
4. Update application configuration

The new system is backwards compatible with all existing functionality while providing enterprise-grade database capabilities.

---

**Note**: Ensure your PostgreSQL server is properly secured and backed up for production use. 