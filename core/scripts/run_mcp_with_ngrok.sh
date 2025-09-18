#!/usr/bin/env bash

set -euo pipefail

# Configuration via env vars (with defaults):
#   PORT            - local MCP SSE port (default: 8060)
#   HOST            - bind host for MCP (default: 0.0.0.0)
#   NAME            - MCP server name (default: "Luna Extensions")
#   TOOL_ROOT       - optional custom extensions root
#   NGROK_AUTHTOKEN - required ngrok authtoken
#   NGROK_URL       - full reserved URL (e.g., https://my-luna.ngrok-free.app)
#   NGROK_DOMAIN    - reserved domain/hostname (e.g., my-luna.ngrok-free.app)
#   OAUTH_PROVIDER  - one of: google, github, microsoft (default: google)
#   OAUTH_DOMAIN    - optional, allow only this domain (can be comma-separated)
#   OAUTH_EMAILS    - optional, allow specific emails (comma-separated)
#   MCP_AUTH        - auth mode for FastMCP (none|inmemory|jwt). Default inmemory.
#   MCP_SCOPES      - space-separated scopes for resource access

PORT=${PORT:-8060}
HOST=${HOST:-0.0.0.0}
NAME=${NAME:-"Luna Extensions"}
TOOL_ROOT=${TOOL_ROOT:-}
OAUTH_PROVIDER=${OAUTH_PROVIDER:-google}
MCP_AUTH=${MCP_AUTH:-inmemory}
MCP_SCOPES=${MCP_SCOPES:-}

# Allow using existing ngrok config authtoken if present
NGROK_CONFIG_FILE=${NGROK_CONFIG:-"$HOME/.config/ngrok/ngrok.yml"}
if [[ -n "${NGROK_AUTHTOKEN:-}" ]]; then
  ngrok config add-authtoken "$NGROK_AUTHTOKEN" >/dev/null
else
  if [[ ! -f "$NGROK_CONFIG_FILE" ]] || ! grep -q "^\s*authtoken:\s*\S\+" "$NGROK_CONFIG_FILE" 2>/dev/null; then
    echo "NGROK_AUTHTOKEN is required. Get one at https://ngrok.com" >&2
    exit 1
  fi
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Start ngrok first so we know the public URL for OAuth metadata

NGROK_CMD=(ngrok http "$PORT")
# Use reserved domain if provided
if [[ -n "${NGROK_URL:-}" ]]; then
  NGROK_CMD+=(--url "$NGROK_URL")
elif [[ -n "${NGROK_DOMAIN:-}" ]]; then
  NGROK_CMD+=(--domain "$NGROK_DOMAIN")
fi

# Optional ngrok OAuth edge protection (separate from server OAuth)
if [[ -n "$OAUTH_PROVIDER" ]]; then
  NGROK_CMD+=(--oauth="$OAUTH_PROVIDER")
fi
if [[ -n "${OAUTH_DOMAIN:-}" ]]; then
  IFS=',' read -ra DOMAINS <<< "$OAUTH_DOMAIN"
  for d in "${DOMAINS[@]}"; do
    NGROK_CMD+=(--oauth-allow-domain="$d")
  done
fi
if [[ -n "${OAUTH_EMAILS:-}" ]]; then
  IFS=',' read -ra EMAILS <<< "$OAUTH_EMAILS"
  for e in "${EMAILS[@]}"; do
    NGROK_CMD+=(--oauth-allow-email="$e")
  done
fi

# Run ngrok in background
${NGROK_CMD[*]} >/dev/null &
NGROK_PID=$!
trap 'kill $NGROK_PID 2>/dev/null || true' EXIT INT TERM

PUBLIC_URL=""
if [[ -n "${NGROK_URL:-}" ]]; then
  PUBLIC_URL="$NGROK_URL"
elif [[ -n "${NGROK_DOMAIN:-}" ]]; then
  PUBLIC_URL="https://$NGROK_DOMAIN"
else
  # Poll ngrok API to get public URL
  API="http://127.0.0.1:4040/api/tunnels"
  for i in {1..30}; do
    sleep 1
    URL=$(curl -s "$API" | python -c 'import sys, json; d=json.loads(sys.stdin.read());
  # prefer https
  https=[t for t in d.get("tunnels",[]) if t.get("proto")=="https"]; print(https[0]["public_url"] if https else "")' 2>/dev/null || true)
    if [[ -n "$URL" ]]; then
      PUBLIC_URL="$URL"
      break
    fi
  done
  if [[ -z "$PUBLIC_URL" ]]; then
    echo "Failed to obtain ngrok public URL" >&2
    exit 1
  fi
fi

echo "Public URL: $PUBLIC_URL/sse" >&2

# Start MCP server in background with OAuth enabled and public base URL
MCP_CMD=(python "$PROJECT_ROOT/core/scripts/build_extensions_mcp_server.py" \
  --transport sse --host "$HOST" --port "$PORT" --name "$NAME" \
  --auth "$MCP_AUTH" --public-base-url "$PUBLIC_URL" --scopes "$MCP_SCOPES")
if [[ -n "$TOOL_ROOT" ]]; then
  MCP_CMD+=(--tool-root "$TOOL_ROOT")
fi

echo "Starting MCP server: ${MCP_CMD[*]}" >&2
"${MCP_CMD[@]}" &
MCP_PID=$!
trap 'kill $MCP_PID 2>/dev/null || true; kill $NGROK_PID 2>/dev/null || true' EXIT INT TERM

# Wait on background processes
wait "$MCP_PID" "$NGROK_PID"


