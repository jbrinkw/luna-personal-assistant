"""
Test DEMO_MODE functionality in auth service
"""
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi.testclient import TestClient


def test_demo_mode_enabled():
    """Test that auth service works in demo mode"""
    # Set DEMO_MODE before importing auth_service
    os.environ["DEMO_MODE"] = "true"

    # Import auth service module
    from core.utils import auth_service

    # Reload to pick up environment changes
    import importlib
    importlib.reload(auth_service)

    client = TestClient(auth_service.app)

    # Test /auth/me endpoint - should return demo user without authentication
    response = client.get("/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "demo_user"
    assert data["github_id"] == 0
    assert data["authenticated"] is True
    assert data.get("demo_mode") is True

    # Test /auth/login endpoint - should redirect to / without GitHub OAuth
    response = client.get("/auth/login", follow_redirects=False)
    assert response.status_code == 307  # Redirect
    assert response.headers["location"] == "/"
    assert "session" in response.cookies

    # Clean up
    os.environ.pop("DEMO_MODE", None)


def test_demo_mode_disabled():
    """Test that auth service requires authentication when demo mode is disabled"""
    # Ensure DEMO_MODE is not set
    os.environ.pop("DEMO_MODE", None)

    # Import auth service module
    from core.utils import auth_service

    # Reload to pick up environment changes
    import importlib
    importlib.reload(auth_service)

    client = TestClient(auth_service.app)

    # Test /auth/me endpoint - should return 401 without authentication
    response = client.get("/auth/me")
    assert response.status_code == 401
    data = response.json()
    assert "Not authenticated" in data.get("detail", "")


if __name__ == "__main__":
    print("Testing DEMO_MODE enabled...")
    test_demo_mode_enabled()
    print("✓ DEMO_MODE enabled test passed")

    print("\nTesting DEMO_MODE disabled...")
    test_demo_mode_disabled()
    print("✓ DEMO_MODE disabled test passed")

    print("\n✓ All tests passed!")
