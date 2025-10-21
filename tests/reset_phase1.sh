#!/bin/bash
# Reset script for Phase 1 tests
# Copies active dev directory to test directory

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACTIVE_DIR="$(dirname "$SCRIPT_DIR")"
TEST_DIR="/root/luna/luna-personal-assistant-test"

echo "=========================================="
echo "Phase 1 Test Environment Reset"
echo "=========================================="

# Stop any running Luna processes
echo "Stopping Luna processes..."
pkill -9 -f "luna.sh" 2>/dev/null || true
pkill -9 -f "supervisor.py" 2>/dev/null || true
sleep 2

# Clean test directory
echo "Removing old test environment..."
rm -rf "$TEST_DIR"

# Copy active to test
echo "Copying active directory to test environment..."
cp -r "$ACTIVE_DIR" "$TEST_DIR"

# Ensure log directory exists
mkdir -p "$TEST_DIR/logs"

echo "=========================================="
echo "Environment reset complete"
echo "Test environment ready at: $TEST_DIR"
echo "=========================================="



