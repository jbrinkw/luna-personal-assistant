#!/bin/bash
# Kill all Luna processes aggressively
# Use this to clean up before starting Luna or when things are stuck

echo "=========================================="
echo "Luna Process Killer"
echo "=========================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
RELOAD_CADDY="${REPO_ROOT}/core/scripts/reload_caddy.sh"

# Find and kill all Luna-related processes
echo "Searching for Luna processes..."

# Kill by script/process name patterns
PATTERNS=(
    "luna.sh"
    "supervisor/supervisor.py"
    "core/utils/agent_api.py"
    "core/utils/mcp_server"
    "caddy run"
    "hub_ui.*npm"
    "hub_ui.*vite"
    "extensions/.*/ui/.*node"
    "extensions/.*/services/.*/.*py"
    "automation_memory"
    "demo_extension"
    "home_assistant"
)

KILLED_COUNT=0

for pattern in "${PATTERNS[@]}"; do
    PIDS=$(pgrep -f "$pattern" 2>/dev/null)
    if [ ! -z "$PIDS" ]; then
        echo "Killing processes matching '$pattern':"
        for pid in $PIDS; do
            # Skip this script's own process
            if [ "$pid" = "$$" ]; then
                continue
            fi
            # Skip if it's the kill_luna.sh script itself
            if ps -p $pid -o cmd --no-headers 2>/dev/null | grep -q "kill_luna.sh"; then
                continue
            fi
            PROCESS_INFO=$(ps -p $pid -o pid,cmd --no-headers 2>/dev/null)
            if [ ! -z "$PROCESS_INFO" ]; then
                echo "  - PID $pid: $(echo $PROCESS_INFO | cut -c1-80)"
                kill -9 $pid 2>/dev/null && KILLED_COUNT=$((KILLED_COUNT + 1))
            fi
        done
    fi
done

# Also kill anything listening on Luna ports
echo ""
echo "Checking Luna ports (8443, 5173, 8080, 8765, 9999)..."
for port in 8443 5173 8080 8765 9999; do
    PID=$(lsof -ti :$port 2>/dev/null)
    if [ ! -z "$PID" ]; then
        echo "Killing process on port $port (PID: $PID)"
        kill -9 $PID 2>/dev/null
        KILLED_COUNT=$((KILLED_COUNT + 1))
    fi
done

# Kill any remaining processes in extension UI port range (5200-5299) and service port range (5300-5399)
echo ""
echo "Checking extension UI ports (5200-5299) and service ports (5300-5399)..."
for port in $(seq 5200 5399); do
    PID=$(lsof -ti :$port 2>/dev/null)
    if [ ! -z "$PID" ]; then
        echo "Killing process on port $port (PID: $PID)"
        kill -9 $PID 2>/dev/null
        KILLED_COUNT=$((KILLED_COUNT + 1))
    fi
done

# Wait a moment for processes to die
sleep 2

# Verify cleanup
echo ""
echo "=========================================="
REMAINING=$(ps aux | grep -E "(luna\.sh|supervisor\.py|agent_api\.py|mcp_server)" | grep -v grep | wc -l)
if [ $REMAINING -eq 0 ]; then
    echo "✓ All Luna processes killed successfully"
else
    echo "⚠ Warning: $REMAINING Luna processes may still be running"
    ps aux | grep -E "(luna\.sh|supervisor\.py|agent_api\.py|mcp_server)" | grep -v grep
fi

# Check if ports are free
echo ""
echo "Port status:"
for port in 8443 5173 8080 8765 9999; do
    if lsof -i :$port >/dev/null 2>&1; then
        echo "  Port $port: IN USE (⚠)"
    else
        echo "  Port $port: FREE (✓)"
    fi
done

if [ -x "$RELOAD_CADDY" ]; then
    echo ""
    echo "Requesting Caddy reload..."
    "$RELOAD_CADDY" "kill-luna" || true
fi

echo "=========================================="
echo "Cleanup complete"
echo "=========================================="
