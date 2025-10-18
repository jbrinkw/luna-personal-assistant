#!/bin/bash
# Start script for background_worker service
# No port required for this service

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting background_worker (no port required)" >&2

# Run the Python worker
exec python3 "$SCRIPT_DIR/worker.py"

