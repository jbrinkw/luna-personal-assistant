#!/bin/bash
# Stop all Luna services

echo "Stopping Luna services..."

# Kill processes by port
echo ""
echo "Stopping Agent API (port 8080)..."
lsof -ti:8080 | xargs kill -9 2>/dev/null || echo "  Not running"

echo "Stopping MCP Server (port 8765)..."
lsof -ti:8765 | xargs kill -9 2>/dev/null || echo "  Not running"

echo "Stopping Hub UI (port 5173)..."
lsof -ti:5173 | xargs kill -9 2>/dev/null || echo "  Not running"

echo "Stopping Automation Memory UI (port 5200)..."
lsof -ti:5200 | xargs kill -9 2>/dev/null || echo "  Not running"

echo "Stopping Automation Memory Backend (port 3051)..."
lsof -ti:3051 | xargs kill -9 2>/dev/null || echo "  Not running"

echo ""
echo "All services stopped."
