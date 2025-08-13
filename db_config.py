"""
Unified database configuration and connection helper.

Usage:
- Configure environment variables in a .env file at the repo root (auto-loaded)
- Switch between prod and test by setting DB_ENV=prod|test (default: prod)

Supported env vars:
  DB_ENV=prod|test

  # Prod
  DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_SCHEMA (optional)
  
  # Test (used when DB_ENV=test)
  TEST_DB_HOST, TEST_DB_PORT, TEST_DB_NAME, TEST_DB_USER, TEST_DB_PASSWORD, TEST_DB_SCHEMA (optional)

This module returns psycopg2 connections configured with a DictCursor and
optionally sets the search_path to the specified schema.
"""

from __future__ import annotations

import os
from typing import Dict, Optional

from dotenv import load_dotenv

# Load from root .env if present
load_dotenv()


def _env(key: str, default: Optional[str] = None) -> Optional[str]:
    return os.environ.get(key, default)


def get_db_env() -> str:
    env = (_env("DB_ENV") or "prod").strip().lower()
    if env not in {"prod", "test"}:
        env = "prod"
    return env


def get_db_config() -> Dict[str, str]:
    """Return a dict of psycopg2 connection kwargs based on DB_ENV.

    Recognized keys: host, port, database, user, password.
    """
    env = get_db_env()
    if env == "test":
        return {
            "host": _env("TEST_DB_HOST", _env("DB_HOST", "127.0.0.1")),
            "port": _env("TEST_DB_PORT", _env("DB_PORT", "5432")),
            "database": _env("TEST_DB_NAME", "workout_tracker_test"),
            "user": _env("TEST_DB_USER", _env("DB_USER", "postgres")),
            "password": _env("TEST_DB_PASSWORD", _env("DB_PASSWORD", "")),
        }
    # prod
    return {
        "host": _env("DB_HOST", "192.168.0.239"),
        "port": _env("DB_PORT", "5432"),
        "database": _env("DB_NAME", "workout_tracker"),
        "user": _env("DB_USER", "postgres"),
        "password": _env("DB_PASSWORD", ""),
    }


def get_db_schema() -> Optional[str]:
    env = get_db_env()
    if env == "test":
        return _env("TEST_DB_SCHEMA", _env("DB_SCHEMA"))
    return _env("DB_SCHEMA")


def get_connection(autocommit: bool = False):
    """Create a psycopg2 connection with a DictCursor and optional schema.

    Note: This function imports psycopg2 lazily to avoid hard dependency when
    not used by the caller.
    """
    import psycopg2
    import psycopg2.extras

    def _set_search_path(connection):
        try:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                schema = get_db_schema()
                if schema:
                    cur.execute("SET search_path TO %s", (schema,))
        except Exception:
            pass

    config = get_db_config()
    env = get_db_env()

    # Attempt to connect; if test DB doesn't exist, optionally auto-create it
    try:
        conn = psycopg2.connect(**config)
    except psycopg2.OperationalError as e:
        msg = str(e).lower()
        wants_auto = False
        if "does not exist" in msg:
            if env == "test":
                wants_auto = _env("DB_AUTO_CREATE_TEST", "1") != "0"
            else:
                wants_auto = _env("DB_AUTO_CREATE", "0") == "1"
        if wants_auto:
            admin_db = _env("TEST_DB_ADMIN_DB", _env("DB_ADMIN_DB", "postgres"))
            admin_cfg = dict(config)
            admin_cfg["database"] = admin_db
            admin_conn = psycopg2.connect(**admin_cfg)
            try:
                admin_conn.autocommit = True
                with admin_conn.cursor() as cur:
                    cur.execute(f"CREATE DATABASE {config['database']}")
            finally:
                admin_conn.close()
            conn = psycopg2.connect(**config)
        else:
            raise

    conn.autocommit = autocommit
    _set_search_path(conn)
    return conn


def print_config():
    cfg = get_db_config()
    env = get_db_env()
    schema = get_db_schema() or "(default)"
    print(f"DB env: {env}")
    print("PostgreSQL Configuration:")
    print(f"  Host: {cfg['host']}")
    print(f"  Port: {cfg['port']}")
    print(f"  Database: {cfg['database']}")
    print(f"  User: {cfg['user']}")
    print(f"  Schema: {schema}")
    print(f"  Password: {'*' * len(cfg['password']) if cfg['password'] else '(not set)'}")


if __name__ == "__main__":
    print_config()


