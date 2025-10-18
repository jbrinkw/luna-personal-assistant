#!/bin/bash
# ngrok tunnel for Luna MCP Server
# Much more reliable than localtunnel!

set -e

# Change to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Configuration
MCP_PORT="${MCP_SERVER_PORT:-8765}"
NGROK_DOMAIN="${NGROK_DOMAIN}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================"
echo "Luna MCP Server - ngrok Tunnel"
echo -e "========================================${NC}"

# Validate configuration
if [ -z "$NGROK_DOMAIN" ]; then
    echo -e "${RED}Error: NGROK_DOMAIN not set in .env${NC}"
    echo ""
    echo "Add to your .env file:"
    echo "  NGROK_DOMAIN=your-domain.ngrok-free.dev"
    echo ""
    exit 1
fi

# Check if ngrok auth token is configured
if ! grep -q "authtoken:" ~/.config/ngrok/ngrok.yml 2>/dev/null; then
    echo -e "${RED}Error: ngrok auth token not configured${NC}"
    echo ""
    echo "Run this command first:"
    echo "  ngrok config add-authtoken YOUR_TOKEN"
    echo ""
    echo "Get your token from: https://dashboard.ngrok.com/get-started/your-authtoken"
    exit 1
fi

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo -e "${YELLOW}ngrok not installed. Installing...${NC}"
    
    # Download ngrok
    wget -q https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz -O /tmp/ngrok.tgz || {
        echo -e "${RED}Error: Failed to download ngrok${NC}"
        echo ""
        echo "Install manually:"
        echo "  wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz"
        echo "  tar xvzf ngrok-v3-stable-linux-amd64.tgz"
        echo "  sudo mv ngrok /usr/local/bin/"
        echo ""
        exit 1
    }
    
    # Extract
    tar xzf /tmp/ngrok.tgz -C /tmp
    sudo mv /tmp/ngrok /usr/local/bin/
    rm /tmp/ngrok.tgz
    
    echo -e "${GREEN}✓ ngrok installed${NC}"
fi

# Verify ngrok auth token is configured
echo -e "${GREEN}✓ Auth token already configured${NC}"

# Check if MCP server is running
if ! nc -z 127.0.0.1 "$MCP_PORT" 2>/dev/null; then
    echo -e "${YELLOW}Warning: MCP server not detected on port $MCP_PORT${NC}"
    echo "Make sure to start the MCP server first with:"
    echo "  ./core/scripts/start_mcp_github.sh"
    echo ""
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for existing ngrok processes
EXISTING_PID=$(ps aux | grep "ngrok http.*$MCP_PORT" | grep -v grep | awk '{print $2}' | head -1)
if [ ! -z "$EXISTING_PID" ]; then
    echo -e "${YELLOW}⚠️  Warning: ngrok already running (PID: $EXISTING_PID)${NC}"
    echo ""
    read -p "Kill existing process and start new one? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill "$EXISTING_PID" 2>/dev/null || true
        sleep 2
        echo -e "${GREEN}✓ Killed old process${NC}"
    else
        echo "Exiting..."
        exit 1
    fi
fi

# Start ngrok
echo ""
echo "Starting ngrok tunnel..."
echo "  Local Port:    $MCP_PORT"
echo "  Static Domain: $NGROK_DOMAIN"
echo "  Public URL:    https://$NGROK_DOMAIN"
echo ""
echo -e "${GREEN}Tunnel is now running!${NC}"
echo ""
echo -e "${YELLOW}Note: First-time visitors may see ngrok's disclaimer page.${NC}"
echo -e "${YELLOW}Click 'Visit Site' to continue. This is normal.${NC}"
echo ""
echo -e "${BLUE}Add to Claude:${NC}"
echo "  MCP Server URL: https://$NGROK_DOMAIN"
echo "  OAuth Provider: GITHUB"
echo ""
echo -e "${GREEN}✓ ngrok is much more reliable than localtunnel!${NC}"
echo ""
echo "Press Ctrl+C to stop the tunnel"
echo -e "${BLUE}========================================${NC}"
echo ""

# Run ngrok with static domain
ngrok http "$MCP_PORT" --domain="$NGROK_DOMAIN" --log=stdout

