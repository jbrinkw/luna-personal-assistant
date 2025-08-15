UI Hub (FastAPI)

Lightweight hub to switch between agent dashboards.

Defaults:
- ChefByte → http://localhost:8030
- CoachByte → http://localhost:8031

Override via env:

Unix/macOS (bash/zsh):
```
export AGENT_LINKS="ChefByte:http://localhost:8030,CoachByte:http://localhost:8031"
```

Windows PowerShell:
```
$env:AGENT_LINKS = "ChefByte:http://localhost:8030,CoachByte:http://localhost:8031"
```

Run from repo root:

```
uvicorn ui_hub.main:app --host 0.0.0.0 --port 8032 --reload
```

Open http://localhost:8032


