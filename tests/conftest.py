"""
Pytest configuration and fixtures
"""
import pytest
import time
import requests


@pytest.fixture(scope="session", autouse=True)
def wait_for_services():
    """Wait for all services to be ready before running tests (skip for database tests)."""
    # Skip service check if SKIP_SERVICE_CHECK env var is set
    import os
    if os.getenv('SKIP_SERVICE_CHECK'):
        return
    
    services = {
        "Agent API": "http://127.0.0.1:8080/healthz",
        "Automation Memory Backend": "http://127.0.0.1:3051/healthz",
    }
    
    max_wait = 30  # seconds
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        all_ready = True
        for name, url in services.items():
            try:
                response = requests.get(url, timeout=1)
                if response.status_code != 200:
                    all_ready = False
                    break
            except Exception:
                all_ready = False
                break
        
        if all_ready:
            print("\nAll services are ready!")
            return
        
        time.sleep(1)
    
    pytest.exit("Services did not start in time. Please start all services before running tests.")


@pytest.fixture
def agent_api_url():
    """Agent API base URL."""
    return "http://127.0.0.1:8080"


@pytest.fixture
def am_backend_url():
    """Automation Memory backend URL."""
    return "http://127.0.0.1:3051"

