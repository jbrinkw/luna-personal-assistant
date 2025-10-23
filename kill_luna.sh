#!/bin/bash
# Luna Emergency Stop Script
# Use this to cleanly stop all Luna processes

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "Luna Emergency Stop"
echo "=========================================="

# Function to kill processes gracefully then forcefully
kill_graceful_then_force() {
    local pattern="$1"
    local name="$2"
    
    if pgrep -f "$pattern" > /dev/null 2>&1; then
        echo "[INFO] Stopping $name..."
        pkill -TERM -f "$pattern" 2>/dev/null || true
        sleep 1
        
        if pgrep -f "$pattern" > /dev/null 2>&1; then
            echo "[INFO] Force killing $name..."
            pkill -9 -f "$pattern" 2>/dev/null || true
        fi
    fi
}

# Step 1: Stop systemd service if running
if systemctl is-active luna.service &>/dev/null; then
    echo "[INFO] Stopping luna.service..."
    sudo systemctl stop luna.service
    sleep 2
fi

# Step 2: Remove lockfile
if [ -f "$SCRIPT_DIR/.luna_lock" ]; then
    echo "[INFO] Removing lockfile..."
    rm -f "$SCRIPT_DIR/.luna_lock"
fi

# Step 3: Stop all Luna processes
kill_graceful_then_force "luna.sh" "Luna bootstrap"
kill_graceful_then_force "supervisor/supervisor.py" "Supervisor"
kill_graceful_then_force "core/utils/agent_api.py" "Agent API"
kill_graceful_then_force "core/utils/mcp_server" "MCP Server"
kill_graceful_then_force "hub_ui.*vite" "Hub UI"
kill_graceful_then_force "extensions/.*/ui" "Extension UIs"
kill_graceful_then_force "extensions/.*/services" "Extension Services"
kill_graceful_then_force "caddy run" "Caddy"

# Step 4: Ask about ngrok
read -p "Kill ngrok tunnel? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    kill_graceful_then_force "ngrok http" "ngrok"
else
    echo "[INFO] Preserving ngrok tunnel"
fi

# Step 5: Port-based cleanup
echo "[INFO] Cleaning up Luna ports..."
for port in 5173 8080 8443 8765 9999 $(seq 5200 5399); do
    PID=$(lsof -ti :$port 2>/dev/null)
    if [ -n "$PID" ]; then
        echo "[INFO] Killing process on port $port (PID: $PID)"
        kill -9 $PID 2>/dev/null || true
    fi
done

# Step 6: Remove flags
rm -f "$SCRIPT_DIR/.luna_shutdown" 2>/dev/null
rm -f "$SCRIPT_DIR/.luna_updating" 2>/dev/null

echo ""
echo "=========================================="
echo "Luna stopped successfully"
echo "=========================================="
echo ""
echo "To restart Luna:"
echo "  Via systemd: sudo systemctl start luna"
echo "  Manually:    cd $SCRIPT_DIR && ./luna.sh"
echo ""



