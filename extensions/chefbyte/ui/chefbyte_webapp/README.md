ChefByte Web (FastAPI + Jinja2 + HTMX)

Run locally:

1. Ensure PostgreSQL is configured via root `.env` (see `db_config.py`). Populate/reset with: `python chefbyte/debug/reset_db.py` from repo root.
2. (Optional) Start push tools for taste/saved meals actions: `python -m chefbyte.push_tools --transport http --host 0.0.0.0 --port 8010`.
3. Start the web server from repo root:

```
uvicorn chefbyte_webapp.main:app --host 0.0.0.0 --port 8050 --reload
```

Open `http://localhost:8050`.

Set `CHEFBYTE_PUSH_URL` to override push server URL (default `http://localhost:8010`).


