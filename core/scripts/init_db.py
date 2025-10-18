"""Initialize Luna database schema.

Creates tables for automation_memory extension:
- task_flows
- scheduled_prompts
- memories

All timestamps stored in UTC (TIMESTAMPTZ).
"""
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import psycopg
from psycopg import sql


def get_db_conninfo():
    """Get database connection string from environment."""
    host = os.getenv('DB_HOST', os.getenv('PGHOST', '127.0.0.1'))
    port = os.getenv('DB_PORT', os.getenv('PGPORT', '5432'))
    database = os.getenv('DB_NAME', os.getenv('PGDATABASE', 'luna'))
    user = os.getenv('DB_USER', os.getenv('PGUSER', 'postgres'))
    password = os.getenv('DB_PASSWORD', os.getenv('PGPASSWORD', ''))
    
    return f"host={host} port={port} dbname={database} user={user} password={password}"


def init_database():
    """Initialize database schema."""
    conninfo = get_db_conninfo()
    db_name = os.getenv('DB_NAME', os.getenv('PGDATABASE', 'luna'))
    host = os.getenv('DB_HOST', os.getenv('PGHOST', '127.0.0.1'))
    port = os.getenv('DB_PORT', os.getenv('PGPORT', '5432'))
    
    print(f"Connecting to database: {db_name} at {host}:{port}")
    
    try:
        conn = psycopg.connect(conninfo, autocommit=True)
        cursor = conn.cursor()
        
        print("Creating tables...")
        
        # Create task_flows table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_flows (
                id SERIAL PRIMARY KEY,
                call_name TEXT UNIQUE NOT NULL,
                prompts JSONB NOT NULL DEFAULT '[]'::jsonb,
                agent VARCHAR(255) NOT NULL DEFAULT 'simple_agent',
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("  [OK] task_flows table created")
        
        # Create scheduled_prompts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_prompts (
                id SERIAL PRIMARY KEY,
                time_of_day TEXT NOT NULL,
                days_of_week JSONB NOT NULL DEFAULT '[]'::jsonb,
                prompt TEXT NOT NULL,
                agent VARCHAR(255) NOT NULL DEFAULT 'simple_agent',
                enabled BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("  [OK] scheduled_prompts table created")
        
        # Create memories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id SERIAL PRIMARY KEY,
                content TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("  [OK] memories table created")
        
        # Create flow_executions table for tracking task flow progress
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS flow_executions (
                id SERIAL PRIMARY KEY,
                flow_id INTEGER NOT NULL REFERENCES task_flows(id) ON DELETE CASCADE,
                status VARCHAR(50) NOT NULL DEFAULT 'running',
                current_prompt_index INTEGER DEFAULT 0,
                total_prompts INTEGER NOT NULL DEFAULT 0,
                started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMPTZ,
                error TEXT,
                prompt_results JSONB DEFAULT '[]'::jsonb
            );
        """)
        print("  [OK] flow_executions table created")
        
        # Create indexes for better performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_flows_call_name ON task_flows(call_name);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_scheduled_prompts_enabled ON scheduled_prompts(enabled);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_flow_executions_flow_id ON flow_executions(flow_id);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_flow_executions_status ON flow_executions(status);
        """)
        print("  [OK] Indexes created")
        
        cursor.close()
        conn.close()
        
        print("\nDatabase initialization completed successfully!")
        return 0
    
    except psycopg.Error as e:
        print(f"\nError initializing database: {e}")
        return 1
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        return 1


def main():
    """Main entry point."""
    print("Luna Database Initialization")
    print("=" * 50)
    return init_database()


if __name__ == "__main__":
    sys.exit(main())

