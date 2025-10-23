#!/usr/bin/env python3
"""Test script for Agent API authentication and health check"""
import os
import sys
import requests
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed")

def test_agent_api():
    """Test the Agent API health check and authentication"""
    # Use public Caddy path (domain configured in Caddyfile)
    base_url = "http://lunahub.dev/api/agent"
    api_key = os.getenv("AGENT_API_KEY")
    
    print("="*60)
    print("🧪 Testing Luna Agent API (via Caddy)")
    print("="*60)
    print(f"Base URL: {base_url}")
    print(f"API Key found: {'Yes' if api_key else 'No'}")
    if api_key:
        print(f"API Key: {api_key[:20]}...")
    print()
    
    # Test 1: Root endpoint (no auth required)
    print("Test 1: GET / (no auth)")
    print("-" * 40)
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("✓ Root endpoint accessible")
            print(f"  Message: {data.get('message', 'N/A')}")
            print(f"  Auth required: {data.get('auth', 'N/A')}")
            print(f"  Available agents: {data.get('available_agents', [])}")
        else:
            print(f"✗ Unexpected status: {response.text}")
    except requests.exceptions.ConnectionError:
        print("✗ Connection refused - Agent API is not running")
        print("  Start it with: python core/utils/agent_api.py")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    
    print()
    
    # Test 2: Health check (no auth required)
    print("Test 2: GET /healthz (no auth)")
    print("-" * 40)
    try:
        response = requests.get(f"{base_url}/healthz", timeout=5)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✓ Health check passed")
            print(f"  Response: {response.json()}")
        else:
            print(f"✗ Health check failed: {response.text}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print()
    
    # Test 3: List models WITHOUT auth (should fail)
    print("Test 3: GET /v1/models (no auth - should fail)")
    print("-" * 40)
    try:
        response = requests.get(f"{base_url}/v1/models", timeout=5)
        print(f"Status: {response.status_code}")
        if response.status_code == 401:
            print("✓ Correctly rejected request without auth")
            print(f"  Response: {response.json()}")
        else:
            print(f"✗ Expected 401, got {response.status_code}")
            print(f"  Response: {response.text}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print()
    
    # Test 4: List models WITH auth (should succeed if key exists)
    if api_key:
        print("Test 4: GET /v1/models (with auth)")
        print("-" * 40)
        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.get(f"{base_url}/v1/models", headers=headers, timeout=5)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print("✓ Successfully authenticated")
                models = data.get('data', [])
                print(f"  Found {len(models)} model(s):")
                for model in models:
                    print(f"    - {model.get('id', 'unknown')}")
            else:
                print(f"✗ Auth failed: {response.text}")
        except Exception as e:
            print(f"✗ Error: {e}")
        
        print()
        
        # Test 5: Chat completion WITH auth
        print("Test 5: POST /v1/chat/completions (with auth)")
        print("-" * 40)
        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "model": "simple_agent",
                "messages": [
                    {"role": "user", "content": "Hello, this is a test"}
                ]
            }
            response = requests.post(
                f"{base_url}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print("✓ Chat completion successful")
                content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                print(f"  Response: {content[:100]}...")
            elif response.status_code == 404:
                print("⚠ Model not found (may need to check agent configuration)")
                print(f"  Response: {response.json()}")
            else:
                print(f"✗ Request failed: {response.text}")
        except Exception as e:
            print(f"✗ Error: {e}")
    else:
        print("Test 4: Skipped (no API key found)")
        print("-" * 40)
        print("Set AGENT_API_KEY in .env or start the server to auto-generate")
    
    print()
    print("="*60)
    print("✓ Testing complete!")
    print("="*60)
    return True

if __name__ == "__main__":
    test_agent_api()

