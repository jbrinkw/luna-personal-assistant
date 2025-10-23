#!/bin/bash
# Convenience script to run Automation Memory health check

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT/extensions/automation_memory/backend"
node health_check.js




