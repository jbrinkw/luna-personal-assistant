"""
Luna Supervisor
Main process manager that orchestrates all Luna services
"""
import json
import os
import sys
import threading
from datetime import datetime
from pathlib import Path


class Supervisor:
    def __init__(self, repo_path=None):
        """Initialize supervisor"""
        if repo_path is None:
            # Default to parent directory of supervisor
            self.repo_path = Path(__file__).parent.parent.absolute()
        else:
            self.repo_path = Path(repo_path).absolute()
        
        self.core_path = self.repo_path / "core"
        self.supervisor_path = self.repo_path / "supervisor"
        
        self.master_config_path = self.core_path / "master_config.json"
        self.state_path = self.supervisor_path / "state.json"
        self.update_queue_path = self.core_path / "update_queue.json"
        
        self.master_config = {}
        self.state = {"services": {}}
        
        # Ensure directories exist
        self.core_path.mkdir(parents=True, exist_ok=True)
        self.supervisor_path.mkdir(parents=True, exist_ok=True)
    
    def check_for_update_queue(self):
        """Check if update queue exists and trigger apply_updates if found"""
        if self.update_queue_path.exists():
            print(f"Update queue found at {self.update_queue_path}")
            print("Triggering apply_updates...")
            
            # Copy apply_updates.py to /tmp
            apply_updates_source = self.core_path / "scripts" / "apply_updates.py"
            apply_updates_temp = Path("/tmp/luna_apply_updates.py")
            
            import shutil
            shutil.copy2(apply_updates_source, apply_updates_temp)
            print(f"Copied apply_updates to {apply_updates_temp}")
            
            # Spawn detached process
            import subprocess
            import os
            
            # Make process independent of parent
            process = subprocess.Popen(
                ["python3", str(apply_updates_temp), str(self.repo_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True
            )
            
            print(f"Spawned apply_updates process (PID: {process.pid})")
            print("Exiting supervisor to allow update process to run...")
            
            # Exit supervisor with code 0
            sys.exit(0)
        
        return False
    
    def get_current_date_version(self):
        """Get current date in MM-DD-YY format"""
        now = datetime.now()
        return now.strftime("%m-%d-%y")
    
    def load_or_create_master_config(self):
        """Load existing master_config.json or create default"""
        if self.master_config_path.exists():
            print(f"Loading existing master_config from {self.master_config_path}")
            with open(self.master_config_path, 'r') as f:
                self.master_config = json.load(f)
        else:
            print(f"Creating default master_config at {self.master_config_path}")
            self.master_config = {
                "luna": {
                    "version": self.get_current_date_version(),
                    "timezone": "UTC",
                    "default_llm": "gpt-4"
                },
                "extensions": {},
                "tool_configs": {},
                "port_assignments": {
                    "extensions": {},
                    "services": {}
                }
            }
            self.save_master_config()
    
    def save_master_config(self):
        """Save master_config to disk"""
        with open(self.master_config_path, 'w') as f:
            json.dump(self.master_config, f, indent=2)
        print(f"Saved master_config to {self.master_config_path}")
    
    def load_or_create_state(self):
        """Load existing state.json or create default"""
        if self.state_path.exists():
            print(f"Loading existing state from {self.state_path}")
            with open(self.state_path, 'r') as f:
                self.state = json.load(f)
        else:
            print(f"Creating default state at {self.state_path}")
            self.state = {"services": {}}
            self.save_state()
    
    def save_state(self):
        """Save state to disk"""
        with open(self.state_path, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def get_state(self):
        """Get current state"""
        return self.state
    
    def update_service_status(self, service_name, pid=None, port=None, status=None):
        """Update service status in state.json"""
        if service_name not in self.state["services"]:
            self.state["services"][service_name] = {}
        
        if pid is not None:
            self.state["services"][service_name]["pid"] = pid
        if port is not None:
            self.state["services"][service_name]["port"] = port
        if status is not None:
            self.state["services"][service_name]["status"] = status
        
        self.save_state()
        print(f"Updated service {service_name}: pid={pid}, port={port}, status={status}")
    
    def assign_port(self, port_type, name, requires_port=True):
        """
        Assign port to extension or service
        
        Args:
            port_type: 'extension' or 'service'
            name: extension name or service key (e.g. "extension.service")
            requires_port: whether service requires a port (for services only)
        
        Returns:
            Port number or None
        """
        if port_type == "extension":
            # Extension UI ports: 5200-5299
            assignments = self.master_config["port_assignments"]["extensions"]
            
            if name in assignments:
                print(f"Reusing existing port {assignments[name]} for extension {name}")
                return assignments[name]
            
            # Find next available port
            used_ports = set(assignments.values())
            for port in range(5200, 5300):
                if port not in used_ports:
                    assignments[name] = port
                    self.save_master_config()
                    print(f"Assigned port {port} to extension {name}")
                    return port
            
            raise RuntimeError("No available ports in extension range (5200-5299)")
        
        elif port_type == "service":
            # Service ports: 5300-5399 (or None if doesn't require port)
            assignments = self.master_config["port_assignments"]["services"]
            
            if not requires_port:
                # Service doesn't need a port
                assignments[name] = None
                self.save_master_config()
                print(f"Service {name} does not require port (set to null)")
                return None
            
            if name in assignments:
                print(f"Reusing existing port {assignments[name]} for service {name}")
                return assignments[name]
            
            # Find next available port
            used_ports = set(p for p in assignments.values() if p is not None)
            for port in range(5300, 5400):
                if port not in used_ports:
                    assignments[name] = port
                    self.save_master_config()
                    print(f"Assigned port {port} to service {name}")
                    return port
            
            raise RuntimeError("No available ports in service range (5300-5399)")
        
        else:
            raise ValueError(f"Invalid port_type: {port_type}")
    
    def get_port_mappings(self):
        """Get all port mappings"""
        # Core services have fixed ports
        core_ports = {
            "hub_ui": 5173,
            "agent_api": 8080,
            "mcp_server": 8765,
            "supervisor": 9999
        }
        
        return {
            "core": core_ports,
            "extensions": self.master_config["port_assignments"]["extensions"],
            "services": self.master_config["port_assignments"]["services"]
        }
    
    def startup(self):
        """Main startup flow"""
        print("=" * 60)
        print("Luna Supervisor Starting...")
        print(f"Repository path: {self.repo_path}")
        print("=" * 60)
        
        # Phase 1: Check for update queue
        if self.check_for_update_queue():
            print("(In full implementation, would process updates here)")
        
        # Phase 2: Load or create master config
        self.load_or_create_master_config()
        
        # Phase 3: Load or create state
        self.load_or_create_state()
        
        # Phase 1A: Basic startup complete, ready for API
        print("=" * 60)
        print("Supervisor startup complete")
        print(f"Master config: {self.master_config_path}")
        print(f"State file: {self.state_path}")
        print("API will be available on http://127.0.0.1:9999")
        print("=" * 60)
    
    def run(self):
        """Run supervisor with API server"""
        # Import here to avoid circular import
        import sys
        from pathlib import Path
        
        # Add parent directory to path to enable import
        supervisor_dir = Path(__file__).parent
        if str(supervisor_dir.parent) not in sys.path:
            sys.path.insert(0, str(supervisor_dir.parent))
        
        from supervisor import api
        
        # Initialize API with this supervisor instance
        api.init_api(self)
        
        # Start API server (blocking)
        print("Starting API server on 127.0.0.1:9999...")
        api.run_api(host='127.0.0.1', port=9999)


def main():
    """Main entry point"""
    # Get repo path from command line or use default
    repo_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Create and start supervisor
    supervisor = Supervisor(repo_path=repo_path)
    supervisor.startup()
    supervisor.run()


if __name__ == "__main__":
    main()

