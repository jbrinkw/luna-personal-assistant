#!/bin/bash
# Start automation_memory backend service
# No port argument - uses default port 3051 from .env or server.js default

set -e  # Exit on any error

# Move to the legacy backend directory where server.js lives
DIR="$(cd "$(dirname "$0")"/../../backend && pwd)"
cd "$DIR"

# Install dependencies once if needed
if [ ! -d "node_modules" ]; then
  npm install --silent
fi

# Load .env from project root for AM_API_PORT (default 3051)
export $(grep -v '^#' ../../../.env 2>/dev/null | xargs) || true

PORT=${AM_API_PORT:-3051}

# Check if our backend is already running
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    EXISTING_PID=$(lsof -Pi :$PORT -sTCP:LISTEN -t 2>/dev/null | head -1)
    if [ -n "$EXISTING_PID" ]; then
        # Check if it's a node process running server.js
        if ps -p $EXISTING_PID -o args= 2>/dev/null | grep -q "node.*server.js"; then
            echo "Backend already running on port $PORT (PID: $EXISTING_PID)" >&2
            # Exit cleanly - this prevents duplicate starts
            exit 0
        else
            echo "ERROR: Port $PORT is in use by another process (PID: $EXISTING_PID)" >&2
            exit 1
        fi
    fi
fi

# Small delay to let any previous instance fully start/crash
sleep 2

# Final port check before starting
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "Port $PORT became occupied during startup delay" >&2
    exit 0
fi

echo "[automation-memory] Starting backend on port $PORT..."

# Replace bash process with node (so PID is tracked correctly)
exec node server.js


