#!/bin/bash
# Luna - Start All Services
# Starts Agent API, MCP Server, and Hub UI

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Luna - Starting All Services${NC}"
echo "========================================"

# Change to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please copy .env.example to .env and configure it"
    exit 1
fi

# Load .env
export $(grep -v '^#' .env | xargs)

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 not found${NC}"
    exit 1
fi

# Install all Python dependencies using utility script
echo -e "${YELLOW}Installing Python dependencies...${NC}"
python3 core/scripts/install_deps.py --quiet
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}Warning: Some dependencies failed to install${NC}"
    echo -e "${YELLOW}Run 'python3 core/scripts/install_deps.py -v' for details${NC}"
fi

# Check if database is accessible (optional)
echo -e "${YELLOW}Checking database connection...${NC}"
python3 core/scripts/init_db.py || echo -e "${YELLOW}Warning: Database check failed. Services may not work properly.${NC}"

# Create logs directory
mkdir -p logs

# Start Agent API
echo -e "${GREEN}Starting Agent API on port ${AGENT_API_PORT:-8080}...${NC}"
setsid python3 core/utils/agent_api.py > logs/agent_api.log 2>&1 &
AGENT_API_PID=$!
echo "Agent API PID: $AGENT_API_PID"

# Wait a moment for Agent API to start
sleep 2

# Start MCP Server with GitHub OAuth
echo -e "${GREEN}Starting MCP Server with GitHub OAuth...${NC}"
setsid python3 core/utils/mcp_server_anthropic.py --provider github > logs/mcp_server.log 2>&1 &
MCP_SERVER_PID=$!
echo "MCP Server PID: $MCP_SERVER_PID"

# Wait a moment for MCP Server to start
sleep 3

# Start ngrok tunnel for MCP Server (non-interactive)
echo -e "${GREEN}Starting ngrok tunnel for MCP Server...${NC}"
setsid bash -c '
    export $(grep -v "^#" .env | xargs) 2>/dev/null || true
    MCP_PORT="${MCP_SERVER_PORT:-8765}"
    NGROK_DOMAIN="${NGROK_DOMAIN}"
    
    if [ -n "$NGROK_DOMAIN" ] && command -v ngrok &> /dev/null; then
        # Kill any existing ngrok processes more safely
        ngrok_pids=$(pgrep -x ngrok 2>/dev/null)
        if [ -n "$ngrok_pids" ]; then
            echo "Stopping existing ngrok processes..."
            for pid in $ngrok_pids; do
                kill -TERM "$pid" 2>/dev/null || true
            done
            sleep 1
        fi
        # Start ngrok
        echo "Starting ngrok tunnel on https://$NGROK_DOMAIN"
        exec ngrok http "$MCP_PORT" --domain="$NGROK_DOMAIN" --log=stdout
    else
        echo "Warning: NGROK_DOMAIN not set or ngrok not installed"
        echo "Run manually: ./core/scripts/ngrok_mcp.sh"
        exit 0
    fi
' > logs/ngrok.log 2>&1 &
NGROK_PID=$!
echo "ngrok PID: $NGROK_PID"

# Wait a moment for ngrok to start
sleep 2

## NOTE: Extension UIs and Services are now auto-started by the Agent API service manager.
echo -e "${GREEN}Extension UIs and Services will be auto-started by Agent API on startup${NC}"

# Start Hub UI (if exists)
if [ -d "hub_ui" ]; then
    echo -e "${GREEN}Starting Hub UI on port ${HUB_UI_PORT:-5173}...${NC}"
    cd hub_ui
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}Installing Hub UI dependencies...${NC}"
        npm install
    fi
    
    # Start UI in background
    setsid npm run dev > ../logs/hub_ui.log 2>&1 &
    HUB_UI_PID=$!
    echo "Hub UI PID: $HUB_UI_PID"
    
    cd "$PROJECT_ROOT"
else
    echo -e "${YELLOW}Hub UI not found, skipping...${NC}"
    HUB_UI_PID=""
fi

# Save PIDs to file for cleanup
echo "$AGENT_API_PID" > logs/agent_api.pid
echo "$MCP_SERVER_PID" > logs/mcp_server.pid
echo "$NGROK_PID" > logs/ngrok.pid
# No per-extension PIDs tracked here; managed by Agent API service manager
if [ -n "$HUB_UI_PID" ]; then
    echo "$HUB_UI_PID" > logs/hub_ui.pid
fi

echo ""
echo -e "${GREEN}All services started successfully!${NC}"
echo "========================================"
echo -e "Agent API:    ${GREEN}http://127.0.0.1:${AGENT_API_PORT:-8080}${NC}"
echo -e "MCP Server:   ${GREEN}http://127.0.0.1:8765${NC} (GitHub OAuth enabled)"
echo -e "ngrok Tunnel: ${GREEN}Check logs/ngrok.log for public URL${NC}"
if [ -n "$HUB_UI_PID" ]; then
    echo -e "Hub UI:     ${GREEN}http://127.0.0.1:${HUB_UI_PORT:-5173}${NC}"
fi
# UIs will be served on 5200–5299, consult /extensions API
echo ""
echo "Logs:"
echo "  - logs/agent_api.log"
echo "  - logs/mcp_server.log"
echo "  - logs/ngrok.log"
if [ -n "$AM_BACKEND_PID" ]; then
    echo "  - logs/am_backend.log"
    echo "  - logs/am_ui.log"
fi
if [ -n "$HUB_UI_PID" ]; then
    echo "  - logs/hub_ui.log"
fi
echo ""
echo "To stop all services, run: ./core/scripts/stop_all.sh"
echo "Or manually kill PIDs from logs/*.pid files"

