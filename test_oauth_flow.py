#!/usr/bin/env python3
"""Test the complete OAuth flow that Claude.ai would go through"""
import requests
import json

BASE_URL = "https://lunahub.dev/api/mcp"

print("=" * 60)
print("Testing OAuth Flow (simulating Claude.ai)")
print("=" * 60)

# Step 1: Discover OAuth configuration
print("\n[Step 1] Discover OAuth protected resource...")
response = requests.get(f"{BASE_URL}/.well-known/oauth-protected-resource")
print(f"Status: {response.status_code}")
protected_resource = response.json()
print(json.dumps(protected_resource, indent=2))

# Step 2: Discover authorization server
print("\n[Step 2] Discover authorization server...")
response = requests.get(f"{BASE_URL}/.well-known/oauth-authorization-server")
print(f"Status: {response.status_code}")
auth_server = response.json()
print(json.dumps(auth_server, indent=2))

# Step 3: Register as a dynamic client (what Claude does)
print("\n[Step 3] Register as dynamic client...")
client_metadata = {
    "client_name": "Claude.ai Test",
    "redirect_uris": ["https://claude.ai/oauth/callback"],
    "grant_types": ["authorization_code", "refresh_token"],
    "response_types": ["code"],
    "token_endpoint_auth_method": "client_secret_post"
}
response = requests.post(
    f"{BASE_URL}/register",
    json=client_metadata,
    headers={"Content-Type": "application/json"}
)
print(f"Status: {response.status_code}")
if response.status_code == 200 or response.status_code == 201:
    client_creds = response.json()
    print(f"✅ Client registered!")
    print(f"Client ID: {client_creds.get('client_id')}")
    print(f"Client Secret: {client_creds.get('client_secret')[:20]}...")
    
    # Step 4: Test authorization endpoint
    print("\n[Step 4] Test authorization endpoint...")
    auth_params = {
        "client_id": client_creds['client_id'],
        "redirect_uri": "https://claude.ai/oauth/callback",
        "response_type": "code",
        "scope": "user"
    }
    # Don't follow redirects to see what happens
    response = requests.get(
        f"{BASE_URL}/authorize",
        params=auth_params,
        allow_redirects=False
    )
    print(f"Status: {response.status_code}")
    if 'Location' in response.headers:
        print(f"Redirects to: {response.headers['Location'][:100]}...")
    else:
        print(f"Response: {response.text[:200]}")
else:
    print(f"❌ Registration failed")
    print(f"Response: {response.text}")

print("\n" + "=" * 60)
print("Test complete")
print("=" * 60)

