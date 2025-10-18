#!/bin/bash
# Check if UI can reach the backend

echo "==================================="
echo "UI Connection Test"
echo "==================================="
echo ""
echo "1. Testing Backend API..."
if curl -s http://127.0.0.1:3051/healthz | grep -q "ok"; then
    echo "   ✓ Backend is responding"
else
    echo "   ✗ Backend is NOT responding"
    exit 1
fi

echo ""
echo "2. Testing UI is serving..."
if curl -s http://127.0.0.1:5200/ | grep -q "Automation Memory"; then
    echo "   ✓ UI is serving"
else
    echo "   ✗ UI is NOT serving"
    exit 1
fi

echo ""
echo "==================================="
echo "✅ ALL TESTS PASSED"
echo "==================================="
echo ""
echo "If the browser still shows 'Disconnected':"
echo ""
echo "1. Hard refresh the browser:"
echo "   • Chrome/Firefox: Ctrl+Shift+R (Cmd+Shift+R on Mac)"
echo "   • Or open DevTools (F12) and right-click refresh button → 'Empty Cache and Hard Reload'"
echo ""
echo "2. Check browser console (F12) for errors"
echo ""
echo "3. Try accessing directly:"
echo "   http://127.0.0.1:5200"
echo ""
