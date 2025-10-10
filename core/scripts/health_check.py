#!/usr/bin/env python3
"""
Health Check Script for Luna Services
Checks all servers, discovered agents, and extensions
"""
import os
import sys
import json
import requests
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def check_service(name: str, url: str, timeout: int = 2) -> bool:
    """Check if a service is responding."""
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            print(f"  {Colors.GREEN}[OK]{Colors.END} {name}: {Colors.GREEN}Online{Colors.END} ({url})")
            return True
        else:
            print(f"  {Colors.RED}[!!]{Colors.END} {name}: {Colors.YELLOW}Responding but status {response.status_code}{Colors.END}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"  {Colors.RED}[XX]{Colors.END} {name}: {Colors.RED}Offline{Colors.END} ({url})")
        return False
    except requests.exceptions.Timeout:
        print(f"  {Colors.RED}[!!]{Colors.END} {name}: {Colors.YELLOW}Timeout{Colors.END} ({url})")
        return False
    except Exception as e:
        print(f"  {Colors.RED}[!!]{Colors.END} {name}: {Colors.RED}Error - {e}{Colors.END}")
        return False

def get_discovered_agents(agent_api_url: str) -> List[Dict]:
    """Get list of discovered agents from Agent API."""
    try:
        response = requests.get(f"{agent_api_url}/v1/models", timeout=2)
        if response.status_code == 200:
            data = response.json()
            return data.get("data", [])
        return []
    except Exception:
        return []

def discover_local_agents() -> List[str]:
    """Discover agents locally by scanning core/agents/."""
    agents_dir = PROJECT_ROOT / "core" / "agents"
    agents = []
    if agents_dir.exists():
        for agent_dir in agents_dir.iterdir():
            if agent_dir.is_dir() and (agent_dir / "agent.py").exists():
                agents.append(agent_dir.name)
    return agents

def discover_local_extensions() -> List[Dict]:
    """Discover extensions locally by scanning extensions/."""
    extensions_dir = PROJECT_ROOT / "extensions"
    extensions = []
    if extensions_dir.exists():
        for ext_dir in extensions_dir.iterdir():
            if ext_dir.is_dir() and (ext_dir / "config.json").exists():
                try:
                    with open(ext_dir / "config.json", 'r') as f:
                        config = json.load(f)
                    
                    # Count tools
                    tools_dir = ext_dir / "tools"
                    tool_count = 0
                    if tools_dir.exists():
                        tool_count = len(list(tools_dir.glob("*_tools.py")))
                    
                    extensions.append({
                        "name": config.get("name", ext_dir.name),
                        "path": str(ext_dir),
                        "tools": tool_count,
                        "has_ui": (ext_dir / "ui" / "package.json").exists(),
                        "has_backend": (ext_dir / "backend" / "package.json").exists() or 
                                     (ext_dir / "backend" / "server.py").exists()
                    })
                except Exception:
                    continue
    return extensions

def main():
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}Luna Health Check{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}\n")

    # Check Services
    print(f"{Colors.BOLD}Core Services:{Colors.END}")
    services = {
        "Agent API": "http://127.0.0.1:8080/healthz",
        "MCP Server": "http://127.0.0.1:8765/healthz",
        "Hub UI": "http://127.0.0.1:5173",
    }
    
    service_status = {}
    for name, url in services.items():
        service_status[name] = check_service(name, url)
    
    print(f"\n{Colors.BOLD}Extension Services:{Colors.END}")
    ext_services = {
        "Automation Memory UI": "http://127.0.0.1:5200",
        "Automation Memory Backend": "http://127.0.0.1:3051/healthz",
    }
    
    for name, url in ext_services.items():
        service_status[name] = check_service(name, url)

    # Discovered Agents
    print(f"\n{Colors.BOLD}Discovered Agents:{Colors.END}")
    
    # Try to get from Agent API first
    agents_from_api = get_discovered_agents("http://127.0.0.1:8080")
    if agents_from_api:
        for agent in agents_from_api:
            print(f"  - {Colors.CYAN}{agent['id']}{Colors.END}")
            if agent.get('description'):
                print(f"    {Colors.YELLOW}{agent['description']}{Colors.END}")
    else:
        # Fallback to local discovery
        local_agents = discover_local_agents()
        if local_agents:
            print(f"  {Colors.YELLOW}(Discovered locally - Agent API offline){Colors.END}")
            for agent in local_agents:
                print(f"  - {Colors.CYAN}{agent}{Colors.END}")
        else:
            print(f"  {Colors.RED}No agents discovered{Colors.END}")

    # Discovered Extensions
    print(f"\n{Colors.BOLD}Discovered Extensions:{Colors.END}")
    extensions = discover_local_extensions()
    if extensions:
        for ext in extensions:
            ui_icon = "[UI] " if ext["has_ui"] else ""
            backend_icon = "[BE] " if ext["has_backend"] else ""
            print(f"  - {Colors.MAGENTA}{ext['name']}{Colors.END} {ui_icon}{backend_icon}")
            print(f"    Tools: {ext['tools']}")
            print(f"    Path: {Colors.YELLOW}{ext['path']}{Colors.END}")
    else:
        print(f"  {Colors.RED}No extensions discovered{Colors.END}")

    # Summary
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
    online_count = sum(1 for status in service_status.values() if status)
    total_count = len(service_status)
    
    if online_count == total_count:
        print(f"{Colors.BOLD}{Colors.GREEN}Status: All systems operational ({online_count}/{total_count}){Colors.END}")
    elif online_count > 0:
        print(f"{Colors.BOLD}{Colors.YELLOW}Status: Partial ({online_count}/{total_count} services online){Colors.END}")
    else:
        print(f"{Colors.BOLD}{Colors.RED}Status: All services offline{Colors.END}")
    
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}\n")

    return 0 if online_count == total_count else 1

if __name__ == "__main__":
    sys.exit(main())

