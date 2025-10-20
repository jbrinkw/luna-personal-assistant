#!/bin/bash
# Start automation_memory backend service
# Receives port as $1 from supervisor

set -e  # Exit on any error

# Port is passed as first argument by supervisor
PORT=$1

if [ -z "$PORT" ]; then
  echo "ERROR: No port provided by supervisor" >&2
  exit 1
fi

# Move to the backend directory where server.js lives
DIR="$(cd "$(dirname "$0")"/../../backend && pwd)"
cd "$DIR"

# Install dependencies once if needed
if [ ! -d "node_modules" ]; then
  npm install --silent
fi

# Load .env from project root for other variables
export $(grep -v '^#' ../../../.env 2>/dev/null | xargs) || true

# Export the port for server.js to use
export AM_API_PORT=$PORT

echo "[automation-memory] Starting backend on port $PORT..."

# Replace bash process with node (so PID is tracked correctly)
exec node server.js


