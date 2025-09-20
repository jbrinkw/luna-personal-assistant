#!/usr/bin/env python3
import os
import sys

def main() -> int:
    host = os.getenv("AM_DB_HOST", os.getenv("DB_HOST", "127.0.0.1"))
    port = int(os.getenv("AM_DB_PORT", os.getenv("DB_PORT", "5432")))
    user = os.getenv("AM_DB_USER", os.getenv("DB_USER", "postgres"))
    password = os.getenv("AM_DB_PASSWORD", os.getenv("DB_PASSWORD", ""))
    name = os.getenv("AM_DB_NAME", os.getenv("DB_NAME", "automation_memory"))

    try:
        import psycopg2
        import psycopg2.extras
    except Exception as e:  # noqa: BLE001
        sys.stderr.write("psycopg2 is required to create the database.\n")
        sys.stderr.write(f"Import error: {e}\n")
        return 2

    conn = None
    try:
        # Connect to the default 'postgres' database to manage databases
        conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname="postgres")
        conn.autocommit = True
        cur = conn.cursor()
        # Check existence
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,))
        exists = cur.fetchone() is not None
        if exists:
            print(f"database '{name}' already exists")
            return 0
        # Create the database
        cur.execute(f"CREATE DATABASE \"{name}\"")
        print(f"created database '{name}'")
        return 0
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"error creating database: {e}\n")
        return 1
    finally:
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass

if __name__ == "__main__":
    raise SystemExit(main())


