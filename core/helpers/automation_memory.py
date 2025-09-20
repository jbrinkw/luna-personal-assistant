"""Automation Memory fetch helpers.

Provides a simple function to retrieve all saved automation memories
as a single newline-joined string. Prefers the local Automation Memory
HTTP API if available, with a graceful fallback to direct PostgreSQL
access using environment variables.

Environment variables honored (HTTP):
- AM_API_PORT (default: 3051)

Environment variables honored (Postgres fallback):
- AM_DB_HOST | DB_HOST | PGHOST (default: 127.0.0.1)
- AM_DB_PORT | DB_PORT | PGPORT (default: 5432)
- AM_DB_NAME | DB_NAME | PGDATABASE (default: automation_memory)
- AM_DB_USER | DB_USER | PGUSER (default: postgres)
- AM_DB_PASSWORD | DB_PASSWORD | PGPASSWORD (default: empty)
"""

from __future__ import annotations

import json
import os
import socket
from typing import List, Optional


def _api_base() -> str:
    port = os.getenv("AM_API_PORT", "3051")
    return f"http://localhost:{port}"


def _http_get_memories(limit: Optional[int] = None) -> Optional[List[str]]:
    """Fetch memories via the Automation Memory HTTP API.

    Returns a list of memory content strings or None on failure.
    """
    import urllib.request
    import urllib.error

    try:
        # Quick check to avoid long timeouts if localhost is unreachable
        with socket.create_connection(("127.0.0.1", int(os.getenv("AM_API_PORT", "3051"))), timeout=0.2):
            pass
    except Exception:
        # No local API listener
        return None

    url = f"{_api_base()}/api/memories"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        contents = []
        for item in data:
            try:
                content = item.get("content") if isinstance(item, dict) else None
                if isinstance(content, str) and content.strip():
                    contents.append(content.strip())
            except Exception:
                continue
        if limit is not None and limit >= 0:
            contents = contents[:limit]
        return contents
    except Exception:
        return None


def _pg_get_memories(limit: Optional[int] = None) -> Optional[List[str]]:
    """Fetch memories directly from PostgreSQL using psycopg2.

    Returns a list of memory content strings or None on failure.
    """
    try:
        import psycopg2  # type: ignore
        import psycopg2.extras  # type: ignore
    except Exception:
        return None

    host = os.getenv("AM_DB_HOST") or os.getenv("DB_HOST") or os.getenv("PGHOST") or "127.0.0.1"
    port = int(os.getenv("AM_DB_PORT") or os.getenv("DB_PORT") or os.getenv("PGPORT") or 5432)
    name = os.getenv("AM_DB_NAME") or os.getenv("DB_NAME") or os.getenv("PGDATABASE") or "automation_memory"
    user = os.getenv("AM_DB_USER") or os.getenv("DB_USER") or os.getenv("PGUSER") or "postgres"
    password = os.getenv("AM_DB_PASSWORD") or os.getenv("DB_PASSWORD") or os.getenv("PGPASSWORD") or ""

    conn = None
    try:
        conn = psycopg2.connect(host=host, port=port, dbname=name, user=user, password=password)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if isinstance(limit, int) and limit >= 0:
            cur.execute("SELECT content FROM memories ORDER BY id DESC LIMIT %s", (limit,))
        else:
            cur.execute("SELECT content FROM memories ORDER BY id DESC")
        rows = cur.fetchall() or []
        out: List[str] = []
        for row in rows:
            try:
                content = row.get("content")
                if isinstance(content, str) and content.strip():
                    out.append(content.strip())
            except Exception:
                continue
        cur.close()
        return out
    except Exception:
        return None
    finally:
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass


def fetch_automation_memories_text(limit: Optional[int] = None) -> str:
    """Return all automation memories as a single newline-joined string.

    Attempts HTTP API first, with a fallback to direct PostgreSQL. Returns an
    empty string if none can be fetched or there are no memories.
    """
    # Try HTTP API
    contents = _http_get_memories(limit=limit)
    if contents is None:
        # Fallback to direct PG
        contents = _pg_get_memories(limit=limit)
    if not contents:
        return ""
    return "\n".join(s for s in contents if isinstance(s, str) and s)


__all__ = [
    "fetch_automation_memories_text",
]


