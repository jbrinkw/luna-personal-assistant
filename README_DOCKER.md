## Build and run with Docker

### Prerequisites
- Docker 24+
- Internet access to install dependencies at build time
- API keys (as needed):
  - OPENAI: set `OPENAI_API_KEY`
  - Google Gemini (optional): set `GOOGLE_API_KEY` or `GEMINI_API_KEY`

### Build (or rebuild) the image
Run this any time you pull new code or make local changes; the command copies the current repo contents into the image.
```bash
docker build -t luna-personal-assistant:latest .
```

### Run the container (all-in-one)
The container runs a manager that starts the OpenAI-compatible API and optional UIs/APIs.

### Build and run (single command, env-file only)
Create a `.env` file in the repo root with ports and secrets (example):
```
OPENAI_API_KEY=sk-...
OPENAI_API_PORT=8069
COACH_API_PORT=3001
COACH_UI_PORT=8031
HUB_PORT=8032
AM_UI_PORT=8033
AM_API_PORT=3051
GROCY_IO_WIZ_PORT=3100
```

Build the image and run the container in one command, loading ports and secrets from `.env`:

```bash
docker build -t luna-personal-assistant:latest .
docker run --rm --name luna --env-file .env --network host -v $(pwd)/logs:/app/logs luna-personal-assistant:latest
```

Notes
- This single command rebuilds the image from your current working tree and then starts the container using the variables in `.env`.
- `--network host` makes container services available on the host ports defined in `.env` without explicit `-p` mappings.
- Logs are written to `/app/logs/apps` inside the container; the volume mount maps them to `./logs` on your host.
- If you want to override any `.env` value at runtime, run the container separately with additional `-e` flags (not covered here).

### Verify it’s running
- Health check
```bash
curl -s http://localhost:8069/healthz
```

- List available agents (exposed as "models")
```bash
curl -s http://localhost:8069/v1/models | jq
```

### Quick test (OpenAI-compatible chat)
Suffixed agent IDs are required; example uses `simple-med`.
```bash
curl -s http://localhost:8069/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "simple-med",
    "messages": [
      {"role": "user", "content": "hello"}
    ]
  }' | jq
```

### Environment reference (common)
- `OPENAI_API_KEY`: required for GPT-4.1 family (tiers default to OpenAI models)
- `OPENAI_API_PORT`: OpenAI-compatible server port (default 8069)
- Optional UIs/APIs (only start if the extension directories exist):
  - `COACH_API_PORT` (default 3001)
  - `COACH_UI_PORT` (default 8031)
  - `HUB_PORT` (default 8032)
  - `AM_UI_PORT` (default 8033)
  - `AM_API_PORT` (default 3051)
  - `GROCY_IO_WIZ_PORT` (default 3100)

### Stop the container
```bash
docker stop luna
```


