#!/usr/bin/env bash
set -euo pipefail

CHEF_PORT="${CHEF_PORT:-8050}"
COACH_API_PORT="${COACH_API_PORT:-3001}"
COACH_UI_PORT="${COACH_UI_PORT:-5173}"
HUB_PORT="${HUB_PORT:-8090}"

# Set agent links for hub
export AGENT_LINKS="ChefByte:http://localhost:${CHEF_PORT},CoachByte:http://localhost:${COACH_UI_PORT}"

echo "Starting ChefByte on :${CHEF_PORT}"
python -m uvicorn chefbyte_webapp.main:app --host 0.0.0.0 --port "${CHEF_PORT}" &

echo "Starting CoachByte API on :${COACH_API_PORT}"
PORT="${COACH_API_PORT}" node coachbyte/server.js &

echo "Starting CoachByte UI (Vite) on :${COACH_UI_PORT}"
# Use local vite binary if present to avoid npx prompt
if [ -f "coachbyte/node_modules/vite/bin/vite.js" ]; then
  node coachbyte/node_modules/vite/bin/vite.js --port "${COACH_UI_PORT}" --host 0.0.0.0 &
else
  npx --yes vite --port "${COACH_UI_PORT}" --host 0.0.0.0 &
fi

echo "Starting Hub on :${HUB_PORT}"
python -m uvicorn ui_hub.main:app --host 0.0.0.0 --port "${HUB_PORT}" &

# Wait on background jobs
wait -n


