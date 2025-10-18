#!/bin/bash
# Start all Luna services in foreground with live logging
# Press Ctrl+C to stop all services

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;36m'
NC='\033[0m' # No Color

# Array to track all PIDs
declare -a PIDS=()

# Cleanup function
cleanup() {
    echo -e "\n\n${YELLOW}Received Ctrl+C - Stopping all services...${NC}\n"
    
    # Kill all tracked PIDs only
    for pid in "${PIDS[@]}"; do
        if ps -p $pid > /dev/null 2>&1; then
            echo "Stopping PID: $pid"
            # First try graceful shutdown
            kill -TERM $pid 2>/dev/null && sleep 0.5
            # Check if still running, then force kill
            if ps -p $pid > /dev/null 2>&1; then
                kill -9 $pid 2>/dev/null
            fi
        fi
    done
    
    # Cleanup by ports only if PIDs didn't work (safer than xargs)
    echo "Cleaning up by ports..."
    for port in 8080 8765 3051 5200 5173 4040; do
        port_pids=$(lsof -ti:$port 2>/dev/null)
        if [ -n "$port_pids" ]; then
            for ppid in $port_pids; do
                echo "  Killing process on port $port (PID: $ppid)"
                kill -9 $ppid 2>/dev/null || true
            done
        fi
    done
    
    # Kill ngrok processes
    pkill -f "ngrok http" 2>/dev/null || true
    
    echo -e "\n${GREEN}All services stopped.${NC}\n"
    exit 0
}

# Set trap for Ctrl+C
trap cleanup SIGINT SIGTERM

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Luna - Starting All Services (Foreground)${NC}"
echo -e "${GREEN}======================================${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo -e "${GREEN}======================================${NC}\n"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo -e "${BLUE}Activating virtual environment...${NC}"
    source .venv/bin/activate
    echo -e "${GREEN}Virtual environment activated${NC}\n"
fi

# Create logs directory
mkdir -p logs

echo -e "${BLUE}Starting services...${NC}\n"

# Start Agent API
echo -e "${GREEN}[1/6] Starting Agent API on port 8080...${NC}"
cd core/utils
python3 agent_api.py > ../../logs/agent_api_fg.log 2>&1 &
AGENT_API_PID=$!
PIDS+=($AGENT_API_PID)
echo "  PID: $AGENT_API_PID"
cd "$PROJECT_ROOT"
sleep 2

# Start MCP Server
echo -e "${GREEN}[2/6] Starting MCP Server on port 8765...${NC}"
cd core/utils
python3 mcp_server_anthropic.py --provider github > ../../logs/mcp_fg.log 2>&1 &
MCP_PID=$!
PIDS+=($MCP_PID)
echo "  PID: $MCP_PID"
cd "$PROJECT_ROOT"
sleep 3

# Start ngrok tunnel for MCP Server
echo -e "${GREEN}[2b/6] Starting ngrok tunnel for MCP Server...${NC}"
# Run ngrok in background, skip interactive prompts
cd "$PROJECT_ROOT"
(
    export $(grep -v '^#' .env | xargs) 2>/dev/null || true
    MCP_PORT="${MCP_SERVER_PORT:-8765}"
    NGROK_DOMAIN="${NGROK_DOMAIN}"
    
    if [ -n "$NGROK_DOMAIN" ] && command -v ngrok &> /dev/null; then
        # Kill any existing ngrok on this port
        pkill -f "ngrok http.*$MCP_PORT" 2>/dev/null || true
        sleep 1
        # Start ngrok
        ngrok http "$MCP_PORT" --domain="$NGROK_DOMAIN" --log=stdout > logs/ngrok_fg.log 2>&1 &
        echo "  ngrok PID: $!"
        echo "  Public URL: https://$NGROK_DOMAIN"
    else
        echo "  Skipping (NGROK_DOMAIN not set or ngrok not installed)"
    fi
) &
NGROK_PID=$!
PIDS+=($NGROK_PID)
sleep 2

echo -e "${GREEN}[3/6] Extension UIs and Services will be auto-started by Agent API on startup${NC}"

# Start Hub UI
if [ -d "hub_ui" ]; then
    echo -e "${GREEN}[5/6] Starting Hub UI on port 5173...${NC}"
    cd hub_ui
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}  Installing Hub UI dependencies...${NC}"
        npm install --silent
    fi
    
    npm run dev > ../logs/hub_ui_fg.log 2>&1 &
    HUB_UI_PID=$!
    PIDS+=($HUB_UI_PID)
    echo "  PID: $HUB_UI_PID"
    cd "$PROJECT_ROOT"
    sleep 2
else
    echo -e "${YELLOW}[5/6] Hub UI not found, skipping...${NC}"
fi

# Wait a moment for all services to start
sleep 3

# Run health check
echo -e "\n${BLUE}[6/6] Running health check...${NC}\n"
if [ -f "extensions/automation_memory/backend/health_check.js" ]; then
    cd extensions/automation_memory/backend
    node health_check.js || echo -e "${RED}Health check failed${NC}"
    cd "$PROJECT_ROOT"
else
    echo -e "${YELLOW}Health check script not found${NC}"
fi

echo -e "\n${GREEN}======================================${NC}"
echo -e "${GREEN}All services are running!${NC}"
echo -e "${GREEN}======================================${NC}"
echo -e "\n${BLUE}Services:${NC}"
echo -e "  Agent API:           ${GREEN}http://127.0.0.1:8080${NC}"
echo -e "  MCP Server:          ${GREEN}http://127.0.0.1:8765${NC}"
echo -e "  Hub UI:              ${GREEN}http://127.0.0.1:5173${NC}"
echo -e "  Extensions:          ${GREEN}GET http://127.0.0.1:8080/extensions${NC} for ports and status"
echo -e "\n${BLUE}Logs (live view):${NC}"
echo -e "  • logs/agent_api_fg.log"
echo -e "  • logs/mcp_fg.log"
echo -e "  • logs/ngrok_fg.log"
echo -e "  • logs/am_backend_fg.log"
echo -e "  • logs/am_ui_fg.log"
echo -e "  • logs/hub_ui_fg.log"
echo -e "\n${YELLOW}Press Ctrl+C to stop all services${NC}\n"
echo -e "${GREEN}======================================${NC}\n"

# Show live logs from all services
echo -e "${BLUE}Showing live logs (Ctrl+C to stop):${NC}\n"
echo -e "${BLUE}Use: curl http://127.0.0.1:8080/extensions${NC} to view extension statuses."

# Wait indefinitely (until Ctrl+C)
wait


