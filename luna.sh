#!/bin/bash
# Luna Bootstrap Script
# Minimal launcher that starts supervisor and monitors its health

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUPERVISOR_PY="$SCRIPT_DIR/supervisor/supervisor.py"
HEALTH_URL="http://127.0.0.1:9999/health"
HEALTH_CHECK_INTERVAL=10
MAX_FAILURES=3

echo "=========================================="
echo "Luna Bootstrap Starting"
echo "Repository: $SCRIPT_DIR"
echo "=========================================="

# Function to check if supervisor is running
is_supervisor_running() {
    pgrep -f "supervisor/supervisor.py" > /dev/null 2>&1
    return $?
}

# Function to start supervisor
start_supervisor() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting supervisor..."
    cd "$SCRIPT_DIR"
    python3 "$SUPERVISOR_PY" "$SCRIPT_DIR" > logs/supervisor.log 2>&1 &
    SUPERVISOR_PID=$!
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Supervisor started with PID: $SUPERVISOR_PID"
}

# Function to perform health check
health_check() {
    curl -s -f "$HEALTH_URL" > /dev/null 2>&1
    return $?
}

# Function to kill supervisor
kill_supervisor() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Killing supervisor..."
    pkill -9 -f "supervisor/supervisor.py"
    sleep 1
}

# Create logs directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/logs"

# Initialize failure counter
failure_count=0

# Main monitoring loop
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting monitoring loop..."
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Health check interval: ${HEALTH_CHECK_INTERVAL}s"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Max failures before restart: $MAX_FAILURES"

while true; do
    # Check if supervisor process exists
    if ! is_supervisor_running; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Supervisor not running"
        start_supervisor
        sleep 5
        continue
    fi
    
    # Perform health check
    if health_check; then
        # Health check passed
        if [ $failure_count -gt 0 ]; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Health check passed (recovered)"
        fi
        failure_count=0
    else
        # Health check failed
        failure_count=$((failure_count + 1))
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Health check failed (failure $failure_count/$MAX_FAILURES)"
        
        if [ $failure_count -ge $MAX_FAILURES ]; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Max failures reached, restarting supervisor..."
            kill_supervisor
            failure_count=0
            # Loop will restart supervisor on next iteration
            continue
        fi
    fi
    
    # Wait before next check
    sleep $HEALTH_CHECK_INTERVAL
done


