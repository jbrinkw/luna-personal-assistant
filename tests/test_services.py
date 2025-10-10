"""
Comprehensive Integration Tests for Luna Services
Tests all services, agents, extensions, and health checks
"""
import pytest
import requests
import time
from pathlib import Path

# Service URLs
AGENT_API_URL = "http://127.0.0.1:8080"
MCP_URL = "http://127.0.0.1:8765"
HUB_UI_URL = "http://127.0.0.1:5173"
AM_UI_URL = "http://127.0.0.1:5200"
AM_BACKEND_URL = "http://127.0.0.1:3051"


class TestCoreServices:
    """Test core Luna services."""
    
    def test_agent_api_health(self):
        """Test Agent API health endpoint."""
        response = requests.get(f"{AGENT_API_URL}/healthz", timeout=2)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    
    def test_agent_api_models_list(self):
        """Test Agent API models endpoint returns agents."""
        response = requests.get(f"{AGENT_API_URL}/v1/models", timeout=2)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        agents = [model["id"] for model in data["data"]]
        assert "simple_agent" in agents
        assert "passthrough_agent" in agents
    
    def test_agent_api_cors(self):
        """Test Agent API CORS headers."""
        headers = {"Origin": "http://127.0.0.1:5173"}
        response = requests.get(
            f"{AGENT_API_URL}/healthz",
            headers=headers,
            timeout=2
        )
        assert response.status_code == 200
        # Check CORS headers are present
        assert "access-control-allow-origin" in response.headers or \
               response.headers.get("vary") == "Origin"
    
    def test_hub_ui_accessible(self):
        """Test Hub UI is accessible."""
        response = requests.get(HUB_UI_URL, timeout=2)
        assert response.status_code == 200
        assert "Luna Hub" in response.text or response.headers.get("content-type", "").startswith("text/html")


class TestAutomationMemory:
    """Test Automation Memory extension."""
    
    def test_backend_health(self):
        """Test backend health endpoint."""
        response = requests.get(f"{AM_BACKEND_URL}/healthz", timeout=2)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    
    def test_backend_agents_endpoint(self):
        """Test backend can fetch agents."""
        response = requests.get(f"{AM_BACKEND_URL}/api/agents", timeout=2)
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert len(data["agents"]) >= 2  # simple_agent and passthrough_agent
    
    def test_memories_crud(self):
        """Test memories CRUD operations."""
        # List (should be empty or have items)
        response = requests.get(f"{AM_BACKEND_URL}/api/memories", timeout=2)
        assert response.status_code == 200
        initial_count = len(response.json())
        
        # Create
        test_memory = {"content": "Test memory from integration test"}
        response = requests.post(
            f"{AM_BACKEND_URL}/api/memories",
            json=test_memory,
            timeout=2
        )
        assert response.status_code == 200
        memory_id = response.json()["id"]
        
        # List again (should have one more)
        response = requests.get(f"{AM_BACKEND_URL}/api/memories", timeout=2)
        assert response.status_code == 200
        assert len(response.json()) == initial_count + 1
        
        # Delete
        response = requests.delete(
            f"{AM_BACKEND_URL}/api/memories/{memory_id}",
            timeout=2
        )
        assert response.status_code == 200
    
    def test_task_flows_crud(self):
        """Test task flows CRUD operations."""
        # List
        response = requests.get(f"{AM_BACKEND_URL}/api/task_flows", timeout=2)
        assert response.status_code == 200
        initial_count = len(response.json())
        
        # Create
        test_flow = {
            "call_name": "test_flow",
            "prompts": ["prompt 1", "prompt 2"],
            "agent": "simple_agent"
        }
        response = requests.post(
            f"{AM_BACKEND_URL}/api/task_flows",
            json=test_flow,
            timeout=2
        )
        assert response.status_code == 200
        flow_id = response.json()["id"]
        
        # Update
        update_data = {"agent": "passthrough_agent"}
        response = requests.put(
            f"{AM_BACKEND_URL}/api/task_flows/{flow_id}",
            json=update_data,
            timeout=2
        )
        assert response.status_code == 200
        
        # Delete
        response = requests.delete(
            f"{AM_BACKEND_URL}/api/task_flows/{flow_id}",
            timeout=2
        )
        assert response.status_code == 200
    
    def test_scheduled_prompts_crud(self):
        """Test scheduled prompts CRUD operations."""
        # List
        response = requests.get(f"{AM_BACKEND_URL}/api/scheduled_prompts", timeout=2)
        assert response.status_code == 200
        
        # Create
        test_schedule = {
            "time_of_day": "09:00",
            "days_of_week": [True, True, True, True, True, False, False],
            "prompt": "Test scheduled prompt",
            "agent": "simple_agent",
            "enabled": True
        }
        response = requests.post(
            f"{AM_BACKEND_URL}/api/scheduled_prompts",
            json=test_schedule,
            timeout=2
        )
        assert response.status_code == 200
        schedule_id = response.json()["id"]
        
        # Delete
        response = requests.delete(
            f"{AM_BACKEND_URL}/api/scheduled_prompts/{schedule_id}",
            timeout=2
        )
        assert response.status_code == 200
    
    def test_ui_accessible(self):
        """Test UI is accessible."""
        response = requests.get(AM_UI_URL, timeout=2)
        assert response.status_code == 200


class TestHealthCheck:
    """Test health check script functionality."""
    
    def test_health_check_script_exists(self):
        """Test health check script exists."""
        health_check_path = Path("core/scripts/health_check.py")
        assert health_check_path.exists()
        
        # Check wrapper scripts exist
        assert Path("core/scripts/health_check.sh").exists()
        assert Path("core/scripts/health_check.bat").exists()
    
    def test_stop_scripts_exist(self):
        """Test stop scripts exist."""
        assert Path("core/scripts/stop_all.sh").exists()
        assert Path("core/scripts/stop_all.bat").exists()


class TestAgentDiscovery:
    """Test agent discovery functionality."""
    
    def test_agents_discovered_locally(self):
        """Test agents can be discovered from filesystem."""
        agents_dir = Path("core/agents")
        assert agents_dir.exists()
        
        # Check agent directories exist
        assert (agents_dir / "simple_agent" / "agent.py").exists()
        assert (agents_dir / "passthrough_agent" / "agent.py").exists()
    
    def test_agents_via_api(self):
        """Test agents are discoverable via Agent API."""
        response = requests.get(f"{AGENT_API_URL}/v1/models", timeout=2)
        assert response.status_code == 200
        
        data = response.json()
        agent_ids = [m["id"] for m in data["data"]]
        
        assert "simple_agent" in agent_ids
        assert "passthrough_agent" in agent_ids


class TestExtensionDiscovery:
    """Test extension discovery functionality."""
    
    def test_automation_memory_structure(self):
        """Test automation_memory extension has proper structure."""
        ext_path = Path("extensions/automation_memory")
        assert ext_path.exists()
        
        # Check required files
        assert (ext_path / "config.json").exists()
        assert (ext_path / "readme.md").exists()
        assert (ext_path / "tools").is_dir()
        assert (ext_path / "ui").is_dir()
        assert (ext_path / "backend").is_dir()
        
        # Check tool config
        assert (ext_path / "tools" / "tool_config.json").exists()
        
        # Check UI structure
        assert (ext_path / "ui" / "package.json").exists()
        assert (ext_path / "ui" / "start.sh").exists()
        assert (ext_path / "ui" / "start.bat").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

