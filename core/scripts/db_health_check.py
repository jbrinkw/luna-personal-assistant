import os
import sys
import json
import socket
from typing import Optional, Dict, Any

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass


def _env(key: str, default: Optional[str] = None) -> Optional[str]:
    val = os.getenv(key)
    return val if isinstance(val, str) and val.strip() else default


def _resolve_db_config() -> Dict[str, Any]:
    # Priority: DATABASE_URL > PG* > DB*
    url = _env("DATABASE_URL")
    if url:
        return {"url": url}

    host = _env("PGHOST") or _env("DB_HOST") or _env("POSTGRES_HOST") or "127.0.0.1"
    port = int(_env("PGPORT") or _env("DB_PORT") or _env("POSTGRES_PORT") or 5432)
    name = _env("PGDATABASE") or _env("DB_NAME") or _env("POSTGRES_DB")
    user = _env("PGUSER") or _env("DB_USER") or _env("POSTGRES_USER")
    password = _env("PGPASSWORD") or _env("DB_PASSWORD") or _env("POSTGRES_PASSWORD")
    return {"host": host, "port": port, "database": name, "user": user, "password": password}


def _tcp_probe(host: str, port: int, timeout_secs: float = 3.0) -> Dict[str, Any]:
    try:
        with socket.create_connection((host, port), timeout=timeout_secs):
            return {"reachable": True, "error": None}
    except Exception as e:
        return {"reachable": False, "error": str(e)}


def _sql_probe(cfg: Dict[str, Any]) -> Dict[str, Any]:
    try:
        import psycopg2  # type: ignore
        import psycopg2.extras  # type: ignore
    except Exception as e:
        return {"connected": False, "error": f"psycopg2 not installed: {e}"}

    try:
        if "url" in cfg and isinstance(cfg["url"], str):
            conn = psycopg2.connect(cfg["url"])  # type: ignore[arg-type]
        else:
            conn = psycopg2.connect(
                host=cfg.get("host"),
                port=cfg.get("port"),
                dbname=cfg.get("database"),
                user=cfg.get("user"),
                password=cfg.get("password"),
            )
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        val = cur.fetchone()[0]
        cur.close()
        conn.close()
        return {"connected": True, "select1": int(val)}
    except Exception as e:
        return {"connected": False, "error": str(e)}


def main(argv=None) -> int:
    cfg = _resolve_db_config()
    host = cfg.get("host") if isinstance(cfg, dict) else None
    port = cfg.get("port") if isinstance(cfg, dict) else None
    if isinstance(cfg, dict) and "url" in cfg:
        # Best-effort host/port extraction from URL for TCP probe
        try:
            import urllib.parse as _up
            pr = _up.urlparse(cfg["url"])  # type: ignore[index]
            if pr.hostname:
                host = pr.hostname
            if pr.port:
                port = pr.port
        except Exception:
            pass

    if not isinstance(host, str) or not host:
        host = "127.0.0.1"
    if not isinstance(port, int) or port <= 0:
        port = 5432

    tcp = _tcp_probe(host, port)
    sql = _sql_probe(cfg)

    payload = {
        "config": cfg,
        "tcp_probe": tcp,
        "sql_probe": sql,
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


