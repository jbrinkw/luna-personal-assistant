#!/usr/bin/env python3
"""Test script to check MCP OAuth endpoints"""
import requests
import json

print("=" * 60)
print("MCP OAuth Endpoint Test")
print("=" * 60)

# Test endpoints
base_url = "https://lunahub.dev/api/mcp"
local_url = "http://127.0.0.1:8765/api/mcp"

print(f"\n[TEST 1] Root endpoint (public)")
print(f"  URL: {base_url}")
try:
    response = requests.get(base_url, allow_redirects=False, timeout=5)
    print(f"  Status: {response.status_code}")
    print(f"  Headers: {dict(response.headers)}")
    if response.status_code in [301, 302, 307, 308]:
        print(f"  Redirect to: {response.headers.get('Location')}")
    print(f"  Body (first 200 chars): {response.text[:200]}")
except Exception as e:
    print(f"  ❌ ERROR: {e}")

print(f"\n[TEST 2] Root endpoint (local)")
print(f"  URL: {local_url}")
try:
    response = requests.get(local_url, allow_redirects=False, timeout=5)
    print(f"  Status: {response.status_code}")
    print(f"  Headers: {dict(response.headers)}")
    if response.status_code in [301, 302, 307, 308]:
        print(f"  Redirect to: {response.headers.get('Location')}")
    print(f"  Body (first 200 chars): {response.text[:200]}")
except Exception as e:
    print(f"  ❌ ERROR: {e}")

print(f"\n[TEST 3] Auth login endpoint (public)")
auth_url = f"{base_url}/auth/login"
print(f"  URL: {auth_url}")
try:
    response = requests.get(auth_url, allow_redirects=False, timeout=5)
    print(f"  Status: {response.status_code}")
    print(f"  Headers: {dict(response.headers)}")
    if response.status_code in [301, 302, 307, 308]:
        print(f"  Redirect to: {response.headers.get('Location')}")
    print(f"  Body (first 200 chars): {response.text[:200]}")
except Exception as e:
    print(f"  ❌ ERROR: {e}")

print(f"\n[TEST 4] Auth login endpoint (local)")
auth_url_local = f"{local_url}/auth/login"
print(f"  URL: {auth_url_local}")
try:
    response = requests.get(auth_url_local, allow_redirects=False, timeout=5)
    print(f"  Status: {response.status_code}")
    print(f"  Headers: {dict(response.headers)}")
    if response.status_code in [301, 302, 307, 308]:
        print(f"  Redirect to: {response.headers.get('Location')}")
    print(f"  Body (first 200 chars): {response.text[:200]}")
except Exception as e:
    print(f"  ❌ ERROR: {e}")

print(f"\n[TEST 5] MCP protocol endpoint (SSE)")
sse_url = f"{base_url}/sse"
print(f"  URL: {sse_url}")
try:
    response = requests.get(sse_url, timeout=5, stream=True)
    print(f"  Status: {response.status_code}")
    print(f"  Content-Type: {response.headers.get('content-type')}")
    if response.status_code == 200:
        # Read first few lines
        lines = []
        for i, line in enumerate(response.iter_lines(decode_unicode=True)):
            if i < 10:
                lines.append(line)
            else:
                break
        print(f"  First lines:\n    " + "\n    ".join(lines))
    else:
        print(f"  Body: {response.text[:200]}")
except Exception as e:
    print(f"  ❌ ERROR: {e}")

print("\n" + "=" * 60)
print("Check /root/luna-personal-assistant/logs/mcp_server.log")
print("for corresponding log entries")
print("=" * 60)

