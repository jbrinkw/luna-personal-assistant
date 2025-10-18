#!/bin/bash
# Start script for web_server service
# Receives port as $1

PORT=$1

if [ -z "$PORT" ]; then
    echo "Error: Port argument required" >&2
    exit 1
fi

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting web_server on port $PORT" >&2

# Run the Python server
exec python3 "$SCRIPT_DIR/server.py" "$PORT"

