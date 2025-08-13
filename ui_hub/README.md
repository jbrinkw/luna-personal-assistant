UI Hub (FastAPI)

Lightweight hub to switch between agent dashboards.

Defaults:
- ChefByte → http://localhost:8050
- CoachByte → http://localhost:5173
- ProfessorByte → http://localhost:8001

Override via env:

Unix/macOS (bash/zsh):
```
export AGENT_LINKS="ChefByte:http://localhost:8050,CoachByte:http://localhost:5173,ProfessorByte:http://localhost:8001"
```

Windows PowerShell:
```
$env:AGENT_LINKS = "ChefByte:http://localhost:8050,CoachByte:http://localhost:5173,ProfessorByte:http://localhost:8001"
```

Run from repo root:

```
uvicorn ui_hub.main:app --host 0.0.0.0 --port 8090 --reload
```

Open http://localhost:8090


