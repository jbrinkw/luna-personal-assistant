#!/bin/bash
# Stop all Luna services

set +e  # Don't exit on errors

echo "Stopping Luna services..."

# Function to safely kill process on port
kill_port() {
    local port=$1
    local name=$2
    echo "Stopping $name (port $port)..."
    
    local pids=$(lsof -ti:$port 2>/dev/null)
    if [ -n "$pids" ]; then
        for pid in $pids; do
            # First try graceful shutdown
            kill -TERM "$pid" 2>/dev/null && echo "  Sent SIGTERM to PID $pid"
        done
        # Give processes 2 seconds to shut down gracefully
        sleep 2
        # Force kill any remaining processes
        pids=$(lsof -ti:$port 2>/dev/null)
        if [ -n "$pids" ]; then
            for pid in $pids; do
                kill -9 "$pid" 2>/dev/null && echo "  Force killed PID $pid"
            done
        fi
    else
        echo "  Not running"
    fi
}

# Function to safely kill by PID file
kill_pid_file() {
    local pid_file=$1
    local name=$2
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        echo "Stopping $name (PID $pid)..."
        if kill -0 "$pid" 2>/dev/null; then
            kill -TERM "$pid" 2>/dev/null && echo "  Sent SIGTERM to PID $pid"
            sleep 2
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid" 2>/dev/null && echo "  Force killed PID $pid"
            fi
        else
            echo "  Process not running"
        fi
        rm -f "$pid_file"
    fi
}

echo ""
kill_port 8080 "Agent API"
kill_port 8765 "MCP Server"

# Stop ngrok by PID file first, then by port
if [ -f "logs/ngrok.pid" ]; then
    kill_pid_file "logs/ngrok.pid" "ngrok"
else
    echo "Stopping ngrok..."
    # Find ngrok processes more carefully
    ngrok_pids=$(pgrep -x ngrok 2>/dev/null)
    if [ -n "$ngrok_pids" ]; then
        for pid in $ngrok_pids; do
            kill -TERM "$pid" 2>/dev/null && echo "  Sent SIGTERM to ngrok PID $pid"
        done
        sleep 2
        ngrok_pids=$(pgrep -x ngrok 2>/dev/null)
        if [ -n "$ngrok_pids" ]; then
            for pid in $ngrok_pids; do
                kill -9 "$pid" 2>/dev/null && echo "  Force killed ngrok PID $pid"
            done
        fi
    else
        echo "  Not running"
    fi
fi

kill_port 5173 "Hub UI"
kill_port 5200 "Automation Memory UI"
kill_port 3051 "Automation Memory Backend"

# Clean up any remaining PID files
rm -f logs/agent_api.pid logs/mcp_server.pid logs/hub_ui.pid 2>/dev/null

echo ""
echo "All services stopped."
