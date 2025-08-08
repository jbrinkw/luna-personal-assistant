UI Hub (FastAPI)

Lightweight hub to switch between agent dashboards.

Defaults:
- ChefByte → http://localhost:8050
- CoachByte → http://localhost:3001

Override via env:

```
export AGENT_LINKS="ChefByte:http://localhost:8050,CoachByte:http://localhost:3001"
```

Run from repo root:

```
uvicorn ui_hub.main:app --host 0.0.0.0 --port 8090 --reload
```

Open http://localhost:8090


