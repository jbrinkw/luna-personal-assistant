#!/bin/bash
# Start Luna MCP Server with GitHub OAuth for Anthropic Claude
# ONE domain setup - FastMCP handles everything at the same URL

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Change to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}========================================"
echo "Luna MCP Server - GitHub OAuth Setup"
echo -e "========================================${NC}"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please copy env.example to .env and configure it"
    exit 1
fi

# Load .env
export $(grep -v '^#' .env | xargs)

# Validate configuration
MISSING=0

# Auto-generate MCP_BASE_URL from LT_SUBDOMAIN if not set
if [ -z "$MCP_BASE_URL" ]; then
    if [ -n "$LT_SUBDOMAIN" ]; then
        MCP_BASE_URL="https://${LT_SUBDOMAIN}.loca.lt"
        echo -e "${GREEN}✓ Auto-generated base URL: $MCP_BASE_URL${NC}"
    else
        echo -e "${RED}✗ Neither MCP_BASE_URL nor LT_SUBDOMAIN set in .env${NC}"
        echo "  Set one of:"
        echo "    LT_SUBDOMAIN=your-unique-name"
        echo "    MCP_BASE_URL=https://your-domain.com"
        MISSING=1
    fi
else
    echo -e "${GREEN}✓ Base URL configured${NC}"
fi

if [ -z "$GITHUB_CLIENT_ID" ]; then
    echo -e "${RED}✗ GITHUB_CLIENT_ID not set in .env${NC}"
    echo "  Register OAuth app at: https://github.com/settings/developers"
    MISSING=1
fi

if [ -z "$GITHUB_CLIENT_SECRET" ]; then
    echo -e "${RED}✗ GITHUB_CLIENT_SECRET not set in .env${NC}"
    echo "  Get from your GitHub OAuth app"
    MISSING=1
fi

if [ $MISSING -eq 1 ]; then
    echo ""
    echo -e "${YELLOW}Quick setup guide:${NC}"
    echo "  1. Register OAuth app: https://github.com/settings/developers"
    echo "  2. Set redirect URI: \${MCP_BASE_URL}/auth/callback"
    echo "  3. Add credentials to .env"
    echo ""
    echo "See: SETUP_GITHUB_OAUTH.md for details"
    exit 1
fi

echo -e "${GREEN}✓ Configuration validated${NC}"
echo ""
echo "  MCP URL:    $MCP_BASE_URL"
echo "  GitHub ID:  ${GITHUB_CLIENT_ID:0:20}..."
echo "  Provider:   GitHub"
echo ""

# Check for virtual environment and activate if present
if [ -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
    echo -e "${GREEN}✓ Activated virtual environment${NC}"
    PYTHON_CMD="python"
elif [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
    echo -e "${GREEN}✓ Activated virtual environment${NC}"
    PYTHON_CMD="python"
else
    PYTHON_CMD="python3"
fi

# Check if Python is available
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo -e "${RED}Error: Python not found${NC}"
    exit 1
fi

# Check if MCP server is already running
if lsof -Pi :8765 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}Warning: Port 8765 already in use${NC}"
    read -p "Kill existing process? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        lsof -ti:8765 | xargs kill -9 2>/dev/null || true
        sleep 2
    else
        exit 1
    fi
fi

# Start MCP server with GitHub OAuth
echo -e "${GREEN}Starting MCP server with GitHub OAuth...${NC}"
echo ""
echo -e "${YELLOW}To expose publicly:${NC}"
echo "  Run in another terminal: ./core/scripts/ngrok_mcp.sh"
echo ""
echo "Press Ctrl+C to stop"
echo -e "${BLUE}========================================${NC}"
echo ""

# Run MCP server
$PYTHON_CMD core/utils/mcp_server_anthropic.py --provider github

