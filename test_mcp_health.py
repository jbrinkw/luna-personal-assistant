#!/usr/bin/env python3
"""Test script to check MCP server health endpoint"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

def test_health_check():
    """Test the MCP server health endpoint"""
    
    # Get public URL
    public_url = os.getenv("PUBLIC_URL")
    
    print("=" * 60)
    print("MCP Server Health Check Test")
    print("=" * 60)
    
    # Test 1: Direct localhost health check (what supervisor uses)
    print("\n[TEST 1] Direct localhost health check (supervisor method):")
    local_url = "http://127.0.0.1:8765/healthz"
    print(f"  URL: {local_url}")
    
    try:
        response = requests.get(local_url, timeout=5)
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.json()}")
        if response.status_code == 200:
            print("  ✅ PASS - Health check successful")
        else:
            print("  ❌ FAIL - Non-200 status code")
    except requests.exceptions.ConnectionError:
        print("  ⚠️  MCP server not running on port 8765")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
    
    # Test 2: Public URL health check (if available)
    if public_url:
        print(f"\n[TEST 2] Public URL health check:")
        public_health_url = f"{public_url}/healthz"
        print(f"  URL: {public_health_url}")
        
        try:
            response = requests.get(public_health_url, timeout=10)
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            if response.status_code == 200:
                print("  ✅ PASS - Public health check successful")
            else:
                print("  ❌ FAIL - Non-200 status code")
        except requests.exceptions.ConnectionError:
            print("  ⚠️  Cannot reach public URL (tunnel may not be running)")
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
    else:
        print("\n[TEST 2] Public URL health check:")
        print("  ⚠️  PUBLIC_URL not set in .env - skipping public URL test")
    
    # Test 3: Check if MCP server process is running
    print("\n[TEST 3] Process check:")
    try:
        import subprocess
        result = subprocess.run(
            ["pgrep", "-f", "mcp_server.py"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print(f"  ✅ MCP server process running (PID: {', '.join(pids)})")
        else:
            print("  ⚠️  No MCP server process found")
    except Exception as e:
        print(f"  ❌ ERROR checking process: {e}")
    
    print("\n" + "=" * 60)
    print("Test complete")
    print("=" * 60)

if __name__ == "__main__":
    test_health_check()

