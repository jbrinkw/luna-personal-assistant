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
python3 core/utils/agent_api.py > logs/agent_api.log 2>&1 &
AGENT_API_PID=$!
echo "Agent API PID: $AGENT_API_PID"

# Wait a moment for Agent API to start
sleep 2

# Start MCP Server
echo -e "${GREEN}Starting MCP Server on port 8765...${NC}"
python3 core/utils/mcp_server.py --port 8765 > logs/mcp_server.log 2>&1 &
MCP_SERVER_PID=$!
echo "MCP Server PID: $MCP_SERVER_PID"

# Wait a moment for MCP Server to start
sleep 2

# Start Automation Memory Backend (if exists)
if [ -d "extensions/automation_memory/backend" ]; then
    echo -e "${GREEN}Starting Automation Memory Backend on port 3051...${NC}"
    cd extensions/automation_memory/backend
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}Installing backend dependencies...${NC}"
        npm install
    fi
    
    # Start backend in background
    node server.js > ../../../logs/am_backend.log 2>&1 &
    AM_BACKEND_PID=$!
    echo "Automation Memory Backend PID: $AM_BACKEND_PID"
    
    cd "$PROJECT_ROOT"
    sleep 2
else
    echo -e "${YELLOW}Automation Memory Backend not found, skipping...${NC}"
    AM_BACKEND_PID=""
fi

# Start Automation Memory UI (if exists)
if [ -d "extensions/automation_memory/ui" ]; then
    echo -e "${GREEN}Starting Automation Memory UI on port 5200...${NC}"
    cd extensions/automation_memory/ui
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}Installing UI dependencies...${NC}"
        npm install
    fi
    
    # Start UI in background with port
    PORT=5200 npm run dev > ../../../logs/am_ui.log 2>&1 &
    AM_UI_PID=$!
    echo "Automation Memory UI PID: $AM_UI_PID"
    
    cd "$PROJECT_ROOT"
    sleep 2
else
    echo -e "${YELLOW}Automation Memory UI not found, skipping...${NC}"
    AM_UI_PID=""
fi

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
    npm run dev > ../logs/hub_ui.log 2>&1 &
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
if [ -n "$AM_BACKEND_PID" ]; then
    echo "$AM_BACKEND_PID" > logs/am_backend.pid
fi
if [ -n "$AM_UI_PID" ]; then
    echo "$AM_UI_PID" > logs/am_ui.pid
fi
if [ -n "$HUB_UI_PID" ]; then
    echo "$HUB_UI_PID" > logs/hub_ui.pid
fi

echo ""
echo -e "${GREEN}All services started successfully!${NC}"
echo "========================================"
echo -e "Agent API:  ${GREEN}http://127.0.0.1:${AGENT_API_PORT:-8080}${NC}"
echo -e "MCP Server: ${GREEN}http://127.0.0.1:8765${NC}"
if [ -n "$HUB_UI_PID" ]; then
    echo -e "Hub UI:     ${GREEN}http://127.0.0.1:${HUB_UI_PORT:-5173}${NC}"
fi
if [ -n "$AM_BACKEND_PID" ]; then
    echo -e "Automation Memory: ${GREEN}http://127.0.0.1:5200${NC}"
fi
echo ""
echo "Logs:"
echo "  - logs/agent_api.log"
echo "  - logs/mcp_server.log"
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

