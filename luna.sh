#!/bin/bash
# Luna Bootstrap Script
# Minimal launcher that starts supervisor and monitors its health

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="${LUNA_VENV:-$SCRIPT_DIR/.venv}"
PYTHON_BIN="$VENV_PATH/bin/python3"
SUPERVISOR_PY="$SCRIPT_DIR/supervisor/supervisor.py"

# Load .env file if it exists (for deployment mode and other config)
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a  # automatically export all variables
    source "$SCRIPT_DIR/.env"
    set +a
fi

# Check if venv exists
if [ ! -f "$PYTHON_BIN" ]; then
    echo "[ERROR] Virtual environment not found at $VENV_PATH"
    echo "[ERROR] Run install.sh first to create the virtual environment"
    exit 1
fi

# Configuration
LOCKFILE="$SCRIPT_DIR/.luna_lock"
SHUTDOWN_FLAG="$SCRIPT_DIR/.luna_shutdown"
UPDATE_FLAG="$SCRIPT_DIR/.luna_updating"
RELOAD_CADDY="$SCRIPT_DIR/core/scripts/reload_caddy.sh"
HEALTH_URL="http://127.0.0.1:9999/health"
HEALTH_CHECK_INTERVAL=10
MAX_FAILURES=3
INITIAL_STARTUP_WAIT=10
STARTUP_HEALTH_TIMEOUT=60
SHUTDOWN_REQUESTED=false
RUNNING_UNDER_SYSTEMD=false

# Detect if running under systemd (ONLY check INVOCATION_ID)
if [ -n "$INVOCATION_ID" ]; then
    RUNNING_UNDER_SYSTEMD=true
fi

echo "=========================================="
echo "Luna Bootstrap Starting"
echo "Repository: $SCRIPT_DIR"
if [ "$RUNNING_UNDER_SYSTEMD" = true ]; then
    echo "Mode: systemd service"
else
    echo "Mode: manual execution"
fi
echo "=========================================="

# ============================================================
# LOCK MANAGEMENT
# ============================================================

acquire_lock() {
    if [ -f "$LOCKFILE" ]; then
        LOCK_PID=$(cat "$LOCKFILE" 2>/dev/null)
        if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Another luna.sh instance is already running (PID: $LOCK_PID)"
            if [ "$RUNNING_UNDER_SYSTEMD" = true ]; then
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] This is likely a systemd restart. Waiting for previous instance to exit..."
                sleep 5
                # Try again
                if [ -f "$LOCKFILE" ]; then
                    LOCK_PID=$(cat "$LOCKFILE" 2>/dev/null)
                    if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null; then
                        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Previous instance still running. Exiting."
                        exit 1
                    fi
                fi
            else
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] TIP: Stop the systemd service first: sudo systemctl stop luna"
                exit 1
            fi
        else
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Stale lockfile found, removing..."
            rm -f "$LOCKFILE"
        fi
    fi
    
    echo $$ > "$LOCKFILE"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Lock acquired (PID: $$)"
}

release_lock() {
    if [ -f "$LOCKFILE" ]; then
        LOCK_PID=$(cat "$LOCKFILE" 2>/dev/null)
        if [ "$LOCK_PID" = "$$" ]; then
            rm -f "$LOCKFILE"
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Lock released"
        fi
    fi
}

# Trap lock release on exit
trap 'release_lock' EXIT

# ============================================================
# PORT CLEANUP
# ============================================================

cleanup_luna_ports() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cleaning up Luna ports..."
    
    # Step 1: Check core ports individually (fast, only 5 ports)
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Checking core ports..."
    for port in 5173 8080 8443 8765 9999; do
        PID=$(lsof -ti :$port 2>/dev/null)
        if [ -n "$PID" ]; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Found process on port $port (PID: $PID)"
            kill -TERM $PID 2>/dev/null || true
        fi
    done
    
    # Step 2: Single lsof call for entire extension port range (FAST!)
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Scanning extension ports (5200-5399)..."
    EXTENSION_PIDS=$(lsof -ti :5200-5399 2>/dev/null | sort -u)
    
    if [ -n "$EXTENSION_PIDS" ]; then
        EXTENSION_COUNT=$(echo "$EXTENSION_PIDS" | wc -l)
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Found $EXTENSION_COUNT process(es) on extension ports"
        # Try graceful shutdown
        for PID in $EXTENSION_PIDS; do
            kill -TERM $PID 2>/dev/null || true
        done
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] No processes found on extension ports"
    fi
    
    # Wait for graceful shutdown
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Waiting for graceful shutdown..."
    sleep 3
    
    # Step 3: Force kill any survivors - single lsof call for ALL Luna ports
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Force killing any remaining processes..."
    ALL_SURVIVOR_PIDS=$(lsof -ti :5173,:8080,:8443,:8765,:9999,:5200-5399 2>/dev/null | sort -u)
    
    if [ -n "$ALL_SURVIVOR_PIDS" ]; then
        for PID in $ALL_SURVIVOR_PIDS; do
            kill -9 $PID 2>/dev/null || true
        done
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Killed $(echo "$ALL_SURVIVOR_PIDS" | wc -l) remaining process(es)"
    fi
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Port cleanup complete"
}

# ============================================================
# SERVICE MANAGEMENT
# ============================================================

is_supervisor_running() {
    pgrep -f "supervisor/supervisor.py" > /dev/null 2>&1
    return $?
}

health_check() {
    curl -s -f -m 5 "$HEALTH_URL" > /dev/null 2>&1
    return $?
}

start_supervisor() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting supervisor..."
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] [Bootstrap] Starting supervisor process" >> "$BOOTSTRAP_LOG"
    
    cd "$SCRIPT_DIR"
    "$PYTHON_BIN" "$SUPERVISOR_PY" "$SCRIPT_DIR" > logs/supervisor.log 2>&1 &
    SUPERVISOR_PID=$!
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Supervisor started with PID: $SUPERVISOR_PID"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] [Bootstrap] Supervisor started with PID: $SUPERVISOR_PID" >> "$BOOTSTRAP_LOG"
    
    # Initial startup wait
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Waiting ${INITIAL_STARTUP_WAIT}s for supervisor to initialize..."
    sleep $INITIAL_STARTUP_WAIT
    
    # Validate startup with retries
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Validating supervisor startup..."
    local elapsed=0
    local retry_interval=5
    
    while [ $elapsed -lt $STARTUP_HEALTH_TIMEOUT ]; do
        if health_check; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Supervisor startup successful!"
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] [Bootstrap] Supervisor startup validated" >> "$BOOTSTRAP_LOG"
            return 0
        fi
        
        # Check if process is still alive
        if ! is_supervisor_running; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Supervisor process died during startup"
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] [Bootstrap] Supervisor process died during startup" >> "$BOOTSTRAP_LOG"
            return 1
        fi
        
        sleep $retry_interval
        elapsed=$((elapsed + retry_interval))
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Still waiting for supervisor health check... (${elapsed}s/${STARTUP_HEALTH_TIMEOUT}s)"
    done
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Supervisor failed to become healthy within ${STARTUP_HEALTH_TIMEOUT}s"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] [Bootstrap] Supervisor startup timeout" >> "$BOOTSTRAP_LOG"
    return 1
}

kill_supervisor() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Stopping Luna services..."
    
    # Step 1: Try graceful shutdown via specific process patterns
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Attempting graceful shutdown (SIGTERM)..."
    
    pkill -TERM -f "supervisor/supervisor.py" 2>/dev/null || true
    pkill -TERM -f "core/utils/agent_api.py" 2>/dev/null || true
    pkill -TERM -f "core/utils/mcp_server" 2>/dev/null || true
    pkill -TERM -f "hub_ui.*vite" 2>/dev/null || true
    pkill -TERM -f "extensions/.*/ui" 2>/dev/null || true
    pkill -TERM -f "extensions/.*/services" 2>/dev/null || true
    pkill -TERM -f "caddy run" 2>/dev/null || true
    
    # Wait for graceful shutdown
    sleep 5
    
    # Step 2: Force kill survivors
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Force killing any remaining processes..."
    
    pkill -9 -f "supervisor/supervisor.py" 2>/dev/null || true
    pkill -9 -f "core/utils/agent_api.py" 2>/dev/null || true
    pkill -9 -f "core/utils/mcp_server" 2>/dev/null || true
    pkill -9 -f "hub_ui.*vite" 2>/dev/null || true
    pkill -9 -f "extensions/.*/ui" 2>/dev/null || true
    pkill -9 -f "extensions/.*/services" 2>/dev/null || true
    pkill -9 -f "caddy run" 2>/dev/null || true
    
    # Step 3: Conditionally handle ngrok
    if [ "$RUNNING_UNDER_SYSTEMD" = false ]; then
        # Manual run - kill ngrok too
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Manual run detected, killing ngrok..."
        pkill -9 -f "ngrok http" 2>/dev/null || true
    else
        # Systemd - preserve ngrok across restarts
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Systemd run detected, preserving ngrok tunnel"
    fi
    
    # Step 4: Port-based cleanup as final fallback
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Port-based cleanup (fallback)..."
    for port in 5173 8080 8443 8765 9999 $(seq 5200 5399); do
        PID=$(lsof -ti :$port 2>/dev/null)
        if [ -n "$PID" ]; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Killing process on port $port (PID: $PID)"
            kill -9 $PID 2>/dev/null || true
        fi
    done
    
    sleep 2
    
    # Reload Caddy config if needed
    if [ -x "$RELOAD_CADDY" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Requesting Caddy reload..."
        "$RELOAD_CADDY" "luna.sh-shutdown" || true
    fi
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Luna services stopped"
}

# ============================================================
# SIGNAL HANDLERS
# ============================================================

handle_shutdown() {
    echo ""
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Shutdown signal received (Ctrl+C or SIGTERM)"
    SHUTDOWN_REQUESTED=true
    
    # Create shutdown flag
    touch "$SHUTDOWN_FLAG"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Created shutdown flag"
    
    # Stop all services
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Stopping all Luna services..."
    kill_supervisor
    
    # Verify shutdown
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Verifying all processes stopped..."
    sleep 2
    
    # Final check - kill any stragglers with specific patterns only
    if pgrep -f "supervisor/supervisor.py" > /dev/null 2>&1 || \
       pgrep -f "core/utils/agent_api.py" > /dev/null 2>&1 || \
       pgrep -f "hub_ui.*vite" > /dev/null 2>&1; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Found remaining Luna services, force killing..."
        pkill -9 -f "supervisor/supervisor.py" 2>/dev/null || true
        pkill -9 -f "core/utils/agent_api.py" 2>/dev/null || true
        pkill -9 -f "core/utils/mcp_server" 2>/dev/null || true
        pkill -9 -f "hub_ui.*vite" 2>/dev/null || true
        pkill -9 -f "extensions/.*/ui" 2>/dev/null || true
        pkill -9 -f "extensions/.*/services" 2>/dev/null || true
        pkill -9 -f "caddy run" 2>/dev/null || true
        sleep 1
    fi
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Luna shutdown complete"
    exit 0
}

# Trap signals
trap handle_shutdown SIGINT SIGTERM

# ============================================================
# MAIN STARTUP SEQUENCE
# ============================================================

# Step 1: Check for systemd conflict (manual run only)
if [ "$RUNNING_UNDER_SYSTEMD" = false ]; then
    if systemctl is-active luna.service &>/dev/null 2>&1; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: luna.service is already running via systemd!"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] You cannot run luna.sh manually while the systemd service is active."
        echo ""
        echo "To stop the service first:"
        echo "  sudo systemctl stop luna"
        echo ""
        echo "To disable auto-start:"
        echo "  sudo systemctl disable luna"
        echo ""
        echo "To restart the service (recommended):"
        echo "  sudo systemctl restart luna"
        exit 1
    fi
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Systemd service check: not active (manual run is safe)"
fi

# Step 2: Acquire instance lock
acquire_lock

# Step 3: Clean up ports BEFORE rotating logs
cleanup_luna_ports

# Step 4: Rotate logs directory
if [ -d "$SCRIPT_DIR/logs" ] && [ "$(ls -A $SCRIPT_DIR/logs 2>/dev/null)" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Rotating logs directory..."
    rm -rf "$SCRIPT_DIR/logs.old" 2>/dev/null || true
    mv "$SCRIPT_DIR/logs" "$SCRIPT_DIR/logs.old" 2>/dev/null || true
fi
mkdir -p "$SCRIPT_DIR/logs"

# Create bootstrap log
BOOTSTRAP_LOG="$SCRIPT_DIR/logs/bootstrap.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] [Bootstrap] Luna Bootstrap Starting" >> "$BOOTSTRAP_LOG"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] [Bootstrap] Repository: $SCRIPT_DIR" >> "$BOOTSTRAP_LOG"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] [Bootstrap] Mode: $([ "$RUNNING_UNDER_SYSTEMD" = true ] && echo "systemd" || echo "manual")" >> "$BOOTSTRAP_LOG"

# Step 5: Clean up leftover flags
if [ -f "$SHUTDOWN_FLAG" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cleaning up shutdown flag from previous run"
    rm -f "$SHUTDOWN_FLAG"
fi

if [ -f "$UPDATE_FLAG" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cleaning up update flag from previous run"
    rm -f "$UPDATE_FLAG"
fi

# Step 6: Initialize monitoring state
failure_count=0

# ============================================================
# MAIN MONITORING LOOP
# ============================================================

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
        
        # Check if update flag exists - if so, WAIT
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
            if ! start_supervisor; then
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Failed to start supervisor after updates"
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] [Bootstrap] Supervisor startup failed after updates" >> "$BOOTSTRAP_LOG"
                sleep 30
            fi
            continue
        fi
        
        # Don't restart if shutdown was requested
        if [ "$SHUTDOWN_REQUESTED" = true ]; then
            break
        fi
        
        # Start supervisor
        if ! start_supervisor; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Failed to start supervisor"
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] [Bootstrap] Supervisor startup failed" >> "$BOOTSTRAP_LOG"
            
            # Clean up any partial startup
            kill_supervisor
            
            # Wait before retrying
            sleep 30
        fi
        continue
    fi
    
    # Perform health check
    if health_check; then
        # Health check passed
        if [ $failure_count -gt 0 ]; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Health check passed (recovered from $failure_count failures)"
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
            
            # Kill and restart
            kill_supervisor
            failure_count=0
            
            # Loop will restart supervisor on next iteration
            continue
        fi
    fi
    
    # Wait before next check
    sleep $HEALTH_CHECK_INTERVAL
done

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Monitoring loop exited"
