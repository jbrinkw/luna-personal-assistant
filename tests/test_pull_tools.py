import sys
import types
from fastapi.testclient import TestClient

# Stub the agents package if not present
if "agents" not in sys.modules:
    stub = types.SimpleNamespace(function_tool=lambda f: f)
    sys.modules["agents"] = stub

from servers.pull_server import app

client = TestClient(app)


def test_get_inventory_context_returns_string():
    resp = client.post("/get_inventory_context", json={})
    assert resp.status_code == 200
    assert isinstance(resp.json().get("result"), str)


def test_get_shopping_list_context_returns_string():
    resp = client.post("/get_shopping_list_context", json={})
    assert resp.status_code == 200
    assert isinstance(resp.json().get("result"), str)
