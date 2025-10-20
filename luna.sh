#!/bin/bash
# Luna Bootstrap Script
# Minimal launcher that starts supervisor and monitors its health

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUPERVISOR_PY="$SCRIPT_DIR/supervisor/supervisor.py"
SHUTDOWN_FLAG="$SCRIPT_DIR/.luna_shutdown"
UPDATE_FLAG="$SCRIPT_DIR/.luna_updating"
HEALTH_URL="http://127.0.0.1:9999/health"
SHUTDOWN_URL="http://127.0.0.1:9999/shutdown"
HEALTH_CHECK_INTERVAL=10
MAX_FAILURES=3
SHUTDOWN_REQUESTED=false

echo "=========================================="
echo "Luna Bootstrap Starting"
echo "Repository: $SCRIPT_DIR"
echo "=========================================="

# Function to handle shutdown signals
handle_shutdown() {
    echo ""
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Shutdown signal received"
    SHUTDOWN_REQUESTED=true
    
    # Create shutdown flag so we don't restart if manually started again
    touch "$SHUTDOWN_FLAG"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Created shutdown flag"
    
    # Stop supervisor and all services
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Stopping all Luna services..."
    kill_supervisor
    
    # Verify all processes are stopped
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Verifying all processes stopped..."
    sleep 2
    
    # Double-check and force kill any remaining Luna processes
    if pgrep -f "$SCRIPT_DIR" > /dev/null 2>&1; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Force killing remaining processes..."
        pkill -9 -f "$SCRIPT_DIR"
        sleep 1
    fi
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Luna shutdown complete"
    exit 0
}

# Trap SIGINT (Ctrl+C) and SIGTERM
trap handle_shutdown SIGINT SIGTERM

# Function to check if supervisor is running
is_supervisor_running() {
    pgrep -f "supervisor/supervisor.py" > /dev/null 2>&1
    return $?
}

# Function to start supervisor
start_supervisor() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting supervisor..."
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] [Bootstrap] Starting supervisor process" >> "$BOOTSTRAP_LOG"
    cd "$SCRIPT_DIR"
    python3 "$SUPERVISOR_PY" "$SCRIPT_DIR" > logs/supervisor.log 2>&1 &
    SUPERVISOR_PID=$!
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Supervisor started with PID: $SUPERVISOR_PID"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] [Bootstrap] Supervisor started with PID: $SUPERVISOR_PID" >> "$BOOTSTRAP_LOG"
}

# Function to perform health check
health_check() {
    curl -s -f "$HEALTH_URL" > /dev/null 2>&1
    return $?
}

# Function to kill supervisor and all child processes
kill_supervisor() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Killing supervisor and all child processes..."
    
    # Find supervisor PID
    SUPERVISOR_PID=$(pgrep -f "supervisor/supervisor.py")
    
    if [ -n "$SUPERVISOR_PID" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Found supervisor PID: $SUPERVISOR_PID"
        
        # Get the process group ID
        PGID=$(ps -o pgid= -p "$SUPERVISOR_PID" | tr -d ' ')
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Supervisor PGID: $PGID"
        
        # Kill all Luna-related processes (supervisor, agent_api, hub_ui, extensions)
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Killing all Luna processes..."
        pkill -9 -f "supervisor/supervisor.py"
        pkill -9 -f "core/utils/agent_api.py"
        pkill -9 -f "core/utils/mcp_server"
        pkill -9 -f "hub_ui.*vite"
        pkill -9 -f "extensions/.*/ui"
        pkill -9 -f "extensions/.*/services"
        
        # Also kill any remaining processes in the Luna directory
        pkill -9 -f "$SCRIPT_DIR"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] No supervisor process found"
    fi
    
    sleep 2
}

# Rotate logs directory - keep previous run as logs.old
if [ -d "$SCRIPT_DIR/logs" ]; then
    rm -rf "$SCRIPT_DIR/logs.old" 2>/dev/null || true
    mv "$SCRIPT_DIR/logs" "$SCRIPT_DIR/logs.old" 2>/dev/null || true
fi
mkdir -p "$SCRIPT_DIR/logs"

# Create bootstrap log
BOOTSTRAP_LOG="$SCRIPT_DIR/logs/bootstrap.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] [Bootstrap] Luna Bootstrap Starting" >> "$BOOTSTRAP_LOG"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] [Bootstrap] Repository: $SCRIPT_DIR" >> "$BOOTSTRAP_LOG"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] [Bootstrap] Logs directory rotated (previous saved to logs.old)" >> "$BOOTSTRAP_LOG"

# Clean up any leftover flags from previous run
if [ -f "$SHUTDOWN_FLAG" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cleaning up shutdown flag from previous run"
    rm -f "$SHUTDOWN_FLAG"
fi

if [ -f "$UPDATE_FLAG" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cleaning up update flag from previous run"
    rm -f "$UPDATE_FLAG"
fi

# Initialize failure counter
failure_count=0

# Main monitoring loop
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting monitoring loop..."
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Health check interval: ${HEALTH_CHECK_INTERVAL}s"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Max failures before restart: $MAX_FAILURES"

while true; do
    # Exit loop if shutdown was requested
    if [ "$SHUTDOWN_REQUESTED" = true ]; then
        break
    fi
    
    # Check if supervisor process exists
    if ! is_supervisor_running; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Supervisor not running"
        
        # Check if update flag exists - if so, WAIT (don't restart, don't exit)
        if [ -f "$UPDATE_FLAG" ]; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Update flag detected - waiting for updates to complete..."
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] [Bootstrap] Waiting for apply_updates to finish" >> "$BOOTSTRAP_LOG"
            
            # Wait for update flag to be removed (poll every 5 seconds)
            while [ -f "$UPDATE_FLAG" ]; do
                sleep 5
            done
            
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Update flag removed - updates complete"
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] [Bootstrap] Updates complete, restarting supervisor" >> "$BOOTSTRAP_LOG"
            
            # Reset failure counter since this is a clean restart after updates
            failure_count=0
            
            # Now restart supervisor
            start_supervisor
            sleep 5
            continue
        fi
        
        # Don't restart if shutdown was requested
        if [ "$SHUTDOWN_REQUESTED" = true ]; then
            break
        fi
        
        start_supervisor
        sleep 5
        continue
    fi
    
    # Perform health check
    if health_check; then
        # Health check passed
        if [ $failure_count -gt 0 ]; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Health check passed (recovered)"
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] [Bootstrap] Health check recovered" >> "$BOOTSTRAP_LOG"
        fi
        failure_count=0
    else
        # Health check failed
        failure_count=$((failure_count + 1))
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Health check failed (failure $failure_count/$MAX_FAILURES)"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARN] [Bootstrap] Health check failed (failure $failure_count/$MAX_FAILURES)" >> "$BOOTSTRAP_LOG"
        
        if [ $failure_count -ge $MAX_FAILURES ]; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Max failures reached, restarting supervisor..."
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] [Bootstrap] Max failures reached, restarting supervisor" >> "$BOOTSTRAP_LOG"
            kill_supervisor
            failure_count=0
            # Loop will restart supervisor on next iteration
            continue
        fi
    fi
    
    # Wait before next check
    sleep $HEALTH_CHECK_INTERVAL
done


