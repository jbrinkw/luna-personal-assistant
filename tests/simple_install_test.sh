#!/bin/bash
# Simple test to install the test service and verify it appears in the UI

echo "=========================================="
echo "Simple Install Test"
echo "=========================================="
echo ""

API_BASE="http://localhost:9999"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "1. Checking if supervisor is running..."
if curl -s -f "$API_BASE/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Supervisor is running"
else
    echo -e "${RED}✗${NC} Supervisor is NOT running"
    echo "Please start Luna with: ./luna.sh"
    exit 1
fi

echo ""
echo "2. Cleaning up any previous installation..."
curl -s -X POST "$API_BASE/api/external-services/test_http_server/uninstall" \
    -H "Content-Type: application/json" \
    -d '{"remove_data": true}' > /dev/null 2>&1

pkill -f "test_http_server/server.py" 2>/dev/null || true
sleep 2

echo -e "${GREEN}✓${NC} Cleanup complete"

echo ""
echo "3. Installing test_http_server..."
INSTALL_RESPONSE=$(curl -s -X POST "$API_BASE/api/external-services/test_http_server/install" \
    -H "Content-Type: application/json" \
    -d '{"config": {"port": 9876, "message": "UI Test Service"}}')

if echo "$INSTALL_RESPONSE" | jq -e '.success == true' > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Installation successful"
    echo "Response: $INSTALL_RESPONSE" | jq '.'
else
    echo -e "${RED}✗${NC} Installation failed"
    echo "Response: $INSTALL_RESPONSE"
    exit 1
fi

echo ""
echo "4. Starting the service..."
START_RESPONSE=$(curl -s -X POST "$API_BASE/api/external-services/test_http_server/start")

if echo "$START_RESPONSE" | jq -e '.success == true' > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Service started"
    echo "Response: $START_RESPONSE" | jq '.'
else
    echo -e "${RED}✗${NC} Service start failed"
    echo "Response: $START_RESPONSE"
fi

echo ""
echo "5. Checking if service is in installed list..."
INSTALLED=$(curl -s "$API_BASE/api/external-services/installed")
echo "Installed services:"
echo "$INSTALLED" | jq '.'

if echo "$INSTALLED" | jq -e '.test_http_server' > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Service appears in installed list"
else
    echo -e "${RED}✗${NC} Service NOT in installed list"
    exit 1
fi

echo ""
echo "6. Checking service status..."
STATUS=$(curl -s "$API_BASE/api/external-services/test_http_server/status")
echo "Status: $STATUS" | jq '.'

echo ""
echo "7. Testing direct HTTP health check..."
if curl -s -f "http://localhost:9876/health" > /dev/null 2>&1; then
    HEALTH=$(curl -s "http://localhost:9876/health")
    echo -e "${GREEN}✓${NC} Service is responding to health checks"
    echo "Health response: $HEALTH" | jq '.'
else
    echo -e "${YELLOW}⚠${NC}  Service is NOT responding to health checks (may still be starting)"
fi

echo ""
echo "8. Checking supervisor state..."
STATE=$(curl -s "$API_BASE/services/status")
echo "External services in state:"
echo "$STATE" | jq '.external_services'

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "The service should now appear in the UI at:"
echo "  http://localhost:5173/infrastructure"
echo ""
echo "You can also check:"
echo "  - Logs: cat .luna/logs/test_http_server.log"
echo "  - Config: cat external_services/test_http_server/config.json"
echo "  - Registry: cat .luna/external_services.json"

