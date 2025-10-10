"""Create Luna database if it doesn't exist.

This script connects to the default 'postgres' database to create the 'luna' database.
Run this before init_db.py if the database doesn't exist.
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


def get_admin_conninfo():
    """Get database connection string for connecting to postgres database."""
    host = os.getenv('DB_HOST', os.getenv('PGHOST', '127.0.0.1'))
    port = os.getenv('DB_PORT', os.getenv('PGPORT', '5432'))
    user = os.getenv('DB_USER', os.getenv('PGUSER', 'postgres'))
    password = os.getenv('DB_PASSWORD', os.getenv('PGPASSWORD', ''))
    
    return f"host={host} port={port} dbname=postgres user={user} password={password}"


def create_database():
    """Create luna database if it doesn't exist."""
    conninfo = get_admin_conninfo()
    db_name = os.getenv('DB_NAME', os.getenv('PGDATABASE', 'luna'))
    host = os.getenv('DB_HOST', os.getenv('PGHOST', '127.0.0.1'))
    port = os.getenv('DB_PORT', os.getenv('PGPORT', '5432'))
    
    print(f"Connecting to postgres database at {host}:{port}")
    
    try:
        conn = psycopg.connect(conninfo, autocommit=True)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (db_name,)
        )
        exists = cursor.fetchone()
        
        if exists:
            print(f"Database '{db_name}' already exists.")
        else:
            print(f"Creating database '{db_name}'...")
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name))
            )
            print(f"Database '{db_name}' created successfully!")
        
        cursor.close()
        conn.close()
        return 0
    
    except psycopg.Error as e:
        print(f"\nError creating database: {e}")
        return 1
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        return 1


def main():
    """Main entry point."""
    print("Luna Database Creation")
    print("=" * 50)
    result = create_database()
    
    if result == 0:
        print("\nNext step: Run 'python core/scripts/init_db.py' to create tables")
    
    return result


if __name__ == "__main__":
    sys.exit(main())


