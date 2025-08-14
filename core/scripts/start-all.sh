#!/usr/bin/env bash
set -euo pipefail

CHEF_PORT="${CHEF_PORT:-8050}"
COACH_API_PORT="${COACH_API_PORT:-3001}"
COACH_UI_PORT="${COACH_UI_PORT:-5173}"
HUB_PORT="${HUB_PORT:-8090}"

# Set agent links for hub
export AGENT_LINKS="ChefByte:http://localhost:${CHEF_PORT},CoachByte:http://localhost:${COACH_UI_PORT}"

echo "Starting ChefByte on :${CHEF_PORT}"
pushd ../../extensions/chefbyte/ui/chefbyte_webapp >/dev/null
python -m uvicorn main:app --host 0.0.0.0 --port "${CHEF_PORT}" &
popd >/dev/null

echo "Starting CoachByte API on :${COACH_API_PORT}"
pushd ../../extensions/coachbyte/code/node >/dev/null
PORT="${COACH_API_PORT}" node server.js &
popd >/dev/null

echo "Starting CoachByte UI (Vite) on :${COACH_UI_PORT}"
pushd ../../extensions/coachbyte/ui >/dev/null
export COACH_API_PORT
if [ -f "node_modules/vite/bin/vite.js" ]; then
  node node_modules/vite/bin/vite.js --port "${COACH_UI_PORT}" --host 0.0.0.0 &
else
  npx --yes vite --port "${COACH_UI_PORT}" --host 0.0.0.0 &
fi
popd >/dev/null

echo "Starting Hub on :${HUB_PORT}"
pushd ../hub/ui_hub >/dev/null
python -m uvicorn main:app --host 0.0.0.0 --port "${HUB_PORT}" &
popd >/dev/null

# Wait on background jobs
wait -n


