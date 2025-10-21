"""
Luna Supervisor
Main process manager that orchestrates all Luna services
"""
import json
import os
import sys
import threading
import subprocess
import traceback
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
        self.logs_path = self.repo_path / "logs"
        self.luna_path = self.repo_path / ".luna"
        
        self.master_config_path = self.core_path / "master_config.json"
        self.state_path = self.supervisor_path / "state.json"
        self.update_queue_path = self.core_path / "update_queue.json"
        self.log_file = self.logs_path / "supervisor.log"
        self.external_services_registry_path = self.luna_path / "external_services.json"
        
        self.master_config = {}
        self.state = {"services": {}, "external_services": {}}
        self.processes = {}  # Track spawned processes
        
        # Ensure directories exist
        self.core_path.mkdir(parents=True, exist_ok=True)
        self.supervisor_path.mkdir(parents=True, exist_ok=True)
        self.logs_path.mkdir(parents=True, exist_ok=True)
        self.luna_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize external services manager (import after path setup)
        # Add repo path to sys.path to enable imports
        if str(self.repo_path) not in sys.path:
            sys.path.insert(0, str(self.repo_path))
        
        from core.utils.external_services_manager import ExternalServicesManager
        self.external_services_manager = ExternalServicesManager(self.repo_path)
    
    def log(self, level, message):
        """Write structured log message"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] [Supervisor] {message}\n"
        try:
            with open(self.log_file, 'a') as f:
                f.write(log_line)
        except Exception:
            pass
        # Also print to stdout for supervisor.log redirect
        print(f"[{timestamp}] [{level}] [Supervisor] {message}", flush=True)
    
    def check_for_update_queue(self):
        """Check if update queue exists and trigger apply_updates if found"""
        if self.update_queue_path.exists():
            self.log("INFO", f"Update queue found at {self.update_queue_path}")
            
            # Check retry count to prevent infinite loops
            retry_state_path = self.core_path / "update_retry_count.json"
            retry_count = 0
            
            if retry_state_path.exists():
                try:
                    with open(retry_state_path, 'r') as f:
                        retry_data = json.load(f)
                        retry_count = retry_data.get("count", 0)
                        last_attempt = retry_data.get("last_attempt", "")
                        self.log("INFO", f"Previous retry attempts: {retry_count}, last: {last_attempt}")
                except Exception as e:
                    self.log("WARNING", f"Failed to read retry state: {e}")
            
            # If we've tried 3 times, give up
            if retry_count >= 3:
                self.log("ERROR", "Update failed after 3 attempts, moving queue to failed state")
                failed_queue_path = self.core_path / "update_queue_failed.json"
                import shutil
                shutil.move(str(self.update_queue_path), str(failed_queue_path))
                
                # Clean up retry state
                if retry_state_path.exists():
                    retry_state_path.unlink()
                
                self.log("ERROR", f"Failed queue moved to {failed_queue_path}")
                self.log("INFO", "Continuing with normal startup (no updates will be applied)")
                return False
            
            # Increment retry count
            retry_count += 1
            retry_data = {
                "count": retry_count,
                "last_attempt": datetime.now().isoformat()
            }
            with open(retry_state_path, 'w') as f:
                json.dump(retry_data, f, indent=2)
            
            self.log("INFO", f"Triggering apply_updates (attempt {retry_count}/3)...")
            
            # Create flag file FIRST to signal bootstrap to wait (don't restart supervisor)
            update_flag = self.repo_path / ".luna_updating"
            update_flag.touch()
            self.log("INFO", f"Created update flag: {update_flag}")
            
            # Gracefully shutdown all services
            self.log("INFO", "Shutting down all services before update...")
            self.shutdown_all_services()
            
            # Copy apply_updates.py to /tmp
            apply_updates_source = self.core_path / "scripts" / "apply_updates.py"
            apply_updates_temp = Path("/tmp/luna_apply_updates.py")
            
            import shutil
            shutil.copy2(apply_updates_source, apply_updates_temp)
            self.log("INFO", f"Copied apply_updates to {apply_updates_temp}")
            
            # Open log file for apply_updates output
            apply_updates_log = self.logs_path / "apply_updates.log"
            log_fp = open(apply_updates_log, 'a')
            
            # Spawn detached process with output redirected to log
            process = subprocess.Popen(
                ["python3", str(apply_updates_temp), str(self.repo_path)],
                stdout=log_fp,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True
            )
            
            self.log("INFO", f"Spawned apply_updates process (PID: {process.pid})")
            self.log("INFO", f"Output redirected to {apply_updates_log}")
            self.log("INFO", "Exiting supervisor (bootstrap will restart after update completes)...")
            
            # Exit supervisor with code 0 - bootstrap will wait for update flag to be removed
            sys.exit(0)
        
        return False
    
    def get_current_date_version(self):
        """Get current date in MM-DD-YY format"""
        now = datetime.now()
        return now.strftime("%m-%d-%y")
    
    def load_or_create_master_config(self):
        """Load existing master_config.json or create default"""
        if self.master_config_path.exists():
            self.log("INFO", f"Loading existing master_config from {self.master_config_path}")
            with open(self.master_config_path, 'r') as f:
                self.master_config = json.load(f)
        else:
            self.log("INFO", f"Creating default master_config at {self.master_config_path}")
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
        self.log("INFO", f"Saved master_config to {self.master_config_path}")
    
    def load_or_create_state(self):
        """Clear and create fresh state.json on every startup"""
        self.log("INFO", f"Clearing state and creating fresh state at {self.state_path}")
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
        self.log("INFO", f"Updated service {service_name}: pid={pid}, port={port}, status={status}")
    
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
            "caddy": 8443,
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
    
    def shutdown_all_services(self):
        """Gracefully shutdown all tracked services"""
        import signal
        import time
        
        for service_name, process in self.processes.items():
            if process and process.poll() is None:  # Process still running
                self.log("INFO", f"Stopping {service_name} (PID: {process.pid})")
                try:
                    # Kill entire process group (this kills children too)
                    pgid = os.getpgid(process.pid)
                    self.log("INFO", f"  Killing process group {pgid}")
                    os.killpg(pgid, signal.SIGTERM)  # Send SIGTERM to whole group
                    time.sleep(0.5)
                    
                    # Check if process is still running
                    if process.poll() is None:
                        self.log("INFO", f"  Force killing process group {pgid}")
                        os.killpg(pgid, signal.SIGKILL)  # Force kill if needed
                except ProcessLookupError:
                    self.log("INFO", f"  Process group already terminated")
                except Exception as e:
                    self.log("WARNING", f"  Error stopping {service_name}: {e}")
                    # Fallback to individual process kill
                    try:
                        process.terminate()
                        time.sleep(0.5)
                        if process.poll() is None:
                            process.kill()
                    except:
                        pass
        
        self.log("INFO", "All services stopped")
        self._reload_caddy_config(reason="shutdown-all-services")
    
    def _start_caddy(self):
        """Start Caddy reverse proxy on port 8443"""
        try:
            self.log("INFO", "Starting Caddy reverse proxy...")
            
            # Check if Caddy is installed
            caddy_check = subprocess.run(
                ["which", "caddy"],
                capture_output=True,
                text=True
            )
            
            if caddy_check.returncode != 0:
                self.log("WARNING", "Caddy not found, attempting to install...")
                install_script = self.core_path / "scripts" / "install_caddy.sh"
                if install_script.exists():
                    result = subprocess.run(
                        ["bash", str(install_script)],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode != 0:
                        self.log("ERROR", f"Failed to install Caddy: {result.stderr}")
                        self.update_service_status("caddy", status="failed")
                        return
                else:
                    self.log("ERROR", f"Caddy installation script not found at {install_script}")
                    self.update_service_status("caddy", status="failed")
                    return
            
            # Generate Caddyfile
            self._generate_caddyfile()
            
            caddyfile_path = self.repo_path / ".luna" / "Caddyfile"
            if not caddyfile_path.exists():
                self.log("ERROR", f"Caddyfile not found at {caddyfile_path}")
                self.update_service_status("caddy", status="failed")
                return
            
            log_file = self.logs_path / "caddy.log"
            log_fp = open(log_file, 'w')
            
            # Start Caddy with generated config
            proc = subprocess.Popen(
                ["caddy", "run", "--config", str(caddyfile_path), "--adapter", "caddyfile"],
                stdout=log_fp,
                stderr=subprocess.STDOUT,
                cwd=str(self.repo_path),
                start_new_session=True
            )
            
            self.processes["caddy"] = proc
            self.update_service_status("caddy", pid=proc.pid, port=8443, status="starting")
            self.log("INFO", f"Caddy started with PID {proc.pid} on port 8443")
            
            # Check if process is still running after 1 second and update to running
            import time
            time.sleep(1)
            if proc.poll() is None:  # Process still running
                if "caddy" in self.state.get('services', {}):
                    self.state['services']['caddy']['status'] = 'running'
                    self.save_state()
                self.log("INFO", "Caddy is running")
            else:
                self.log("ERROR", "Caddy process died immediately after start")
                self.update_service_status("caddy", status="failed")
            
        except Exception as e:
            self.log("ERROR", f"Failed to start Caddy: {e}")
            self.log("ERROR", traceback.format_exc())
            self.update_service_status("caddy", status="failed")
    
    def _generate_caddyfile(self):
        """Generate Caddyfile using caddy_config_generator"""
        try:
            from core.utils.caddy_config_generator import generate_caddyfile
            
            self.log("INFO", "Generating Caddyfile...")
            content = generate_caddyfile(self.repo_path)
            self.log("INFO", f"Caddyfile generated ({len(content)} bytes)")
            
        except Exception as e:
            self.log("ERROR", f"Failed to generate Caddyfile: {e}")
            self.log("ERROR", traceback.format_exc())
            raise
    
    def _reload_caddy_config(self, reason: str | None = None) -> bool:
        """Reload Caddy configuration using shared helper."""
        context = f" ({reason})" if reason else ""
        self.log("INFO", f"Reloading Caddy configuration{context}...")
        try:
            from core.utils.caddy_control import reload_caddy as _reload_caddy
        except ImportError as exc:
            self.log("ERROR", f"Unable to import Caddy reload helper: {exc}")
            return False

        try:
            success = _reload_caddy(
                self.repo_path,
                reason=f"supervisor{':' + reason if reason else ''}",
                quiet=True,
            )
        except Exception as exc:  # noqa: BLE001
            self.log("ERROR", f"Caddy reload helper failed: {exc}")
            self.log("ERROR", traceback.format_exc())
            return False

        if success:
            self.log("INFO", "Caddy reload request completed successfully")
        else:
            self.log("WARNING", "Caddy reload helper reported failure")
        return success

    def reload_caddy(self, reason: str | None = None) -> bool:
        """Public wrapper for triggering a Caddy reload."""
        return self._reload_caddy_config(reason=reason)
    
    def _start_agent_api(self):
        """Start Agent API server on port 8080"""
        try:
            self.log("INFO", "Starting Agent API server...")
            agent_api_script = self.core_path / "utils" / "agent_api.py"
            
            if not agent_api_script.exists():
                self.log("ERROR", f"Agent API script not found at {agent_api_script}")
                self.update_service_status("agent_api", status="failed")
                return
            
            log_file = self.logs_path / "agent_api.log"
            log_fp = open(log_file, 'w')
            
            # Spawn agent_api.py process
            proc = subprocess.Popen(
                ["python3", str(agent_api_script)],
                stdout=log_fp,
                stderr=subprocess.STDOUT,
                cwd=str(self.repo_path),
                start_new_session=True
            )
            
            self.processes["agent_api"] = proc
            self.update_service_status("agent_api", pid=proc.pid, port=8080, status="starting")
            self.log("INFO", f"Agent API started with PID {proc.pid} on port 8080")
            
            # Check if process is still running after 1 second and update to running
            import time
            time.sleep(1)
            if proc.poll() is None:  # Process still running
                # Update status only, keep existing pid and port
                if "agent_api" in self.state.get('services', {}):
                    self.state['services']['agent_api']['status'] = 'running'
                    self.save_state()
                self.log("INFO", f"Agent API is running")
            
        except Exception as e:
            self.log("ERROR", f"Failed to start Agent API: {e}")
            self.log("ERROR", traceback.format_exc())
            self.update_service_status("agent_api", status="failed")
    
    def _start_mcp_server(self):
        """Start MCP Server on port 8765"""
        try:
            self.log("INFO", "Starting MCP Server...")
            mcp_server_script = self.core_path / "utils" / "mcp_server.py"
            
            if not mcp_server_script.exists():
                self.log("ERROR", f"MCP Server script not found at {mcp_server_script}")
                self.update_service_status("mcp_server", status="failed")
                return
            
            log_file = self.logs_path / "mcp_server.log"
            log_fp = open(log_file, 'w')
            
            # Spawn mcp_server.py process with localhost binding
            proc = subprocess.Popen(
                ["python3", str(mcp_server_script), "--host", "127.0.0.1"],
                stdout=log_fp,
                stderr=subprocess.STDOUT,
                cwd=str(self.repo_path),
                start_new_session=True
            )
            
            self.processes["mcp_server"] = proc
            self.update_service_status("mcp_server", pid=proc.pid, port=8765, status="starting")
            self.log("INFO", f"MCP Server started with PID {proc.pid} on port 8765")
            
            # Check if process is still running after 1 second and update to running
            import time
            time.sleep(1)
            if proc.poll() is None:  # Process still running
                # Update status only, keep existing pid and port
                if "mcp_server" in self.state.get('services', {}):
                    self.state['services']['mcp_server']['status'] = 'running'
                    self.save_state()
                self.log("INFO", f"MCP Server is running")
            
        except Exception as e:
            self.log("ERROR", f"Failed to start MCP Server: {e}")
            self.log("ERROR", traceback.format_exc())
            self.update_service_status("mcp_server", status="failed")
    
    def _start_hub_ui(self):
        """Start Hub UI on port 5173"""
        try:
            self.log("INFO", "Starting Hub UI...")
            hub_ui_dir = self.repo_path / "hub_ui"
            
            if not hub_ui_dir.exists():
                self.log("ERROR", f"Hub UI directory not found at {hub_ui_dir}")
                self.update_service_status("hub_ui", status="failed")
                return
            
            # Check if node_modules exists, install if needed
            node_modules = hub_ui_dir / "node_modules"
            if not node_modules.exists():
                self.log("INFO", "Installing Hub UI dependencies...")
                install_log = self.logs_path / "hub_ui_install.log"
                install_fp = open(install_log, 'w')
                
                # Try pnpm first, fallback to npm
                import shutil
                if shutil.which('pnpm'):
                    subprocess.run(
                        ["pnpm", "install"],
                        cwd=str(hub_ui_dir),
                        stdout=install_fp,
                        stderr=subprocess.STDOUT
                    )
                else:
                    subprocess.run(
                        ["npm", "install"],
                        cwd=str(hub_ui_dir),
                        stdout=install_fp,
                        stderr=subprocess.STDOUT
                    )
                install_fp.close()
                self.log("INFO", "Hub UI dependencies installed")
            
            log_file = self.logs_path / "hub_ui.log"
            log_fp = open(log_file, 'w')
            
            # Spawn npm run dev
            proc = subprocess.Popen(
                ["npm", "run", "dev"],
                stdout=log_fp,
                stderr=subprocess.STDOUT,
                cwd=str(hub_ui_dir),
                start_new_session=True
            )
            
            self.processes["hub_ui"] = proc
            self.update_service_status("hub_ui", pid=proc.pid, port=5173, status="starting")
            self.log("INFO", f"Hub UI started with PID {proc.pid} on port 5173")
            
            # Check if process is still running after 1 second and update to running
            import time
            time.sleep(1)
            if proc.poll() is None:  # Process still running
                # Update status only, keep existing pid and port
                if "hub_ui" in self.state.get('services', {}):
                    self.state['services']['hub_ui']['status'] = 'running'
                    self.save_state()
                self.log("INFO", f"Hub UI is running")
            
        except Exception as e:
            self.log("ERROR", f"Failed to start Hub UI: {e}")
            self.log("ERROR", traceback.format_exc())
            self.update_service_status("hub_ui", status="failed")
    
    def _start_extension_ui(self, extension_name, extension_path):
        """Start an extension UI"""
        try:
            ui_dir = extension_path / "ui"
            start_script = ui_dir / "start.sh"
            
            if not start_script.exists():
                self.log("INFO", f"No UI for extension {extension_name} (no start.sh found)")
                return
            
            # Assign port
            port = self.assign_port("extension", extension_name)
            
            # Make start.sh executable
            import os
            os.chmod(start_script, 0o755)
            
            # Set environment variables
            env = os.environ.copy()
            env['LUNA_PORTS'] = json.dumps(self.get_port_mappings())
            
            # Open log file
            log_file = self.logs_path / f"{extension_name}_ui.log"
            log_fp = open(log_file, 'w')
            
            # Start the UI
            proc = subprocess.Popen(
                [str(start_script), str(port)],
                stdout=log_fp,
                stderr=subprocess.STDOUT,
                cwd=str(ui_dir),
                env=env,
                start_new_session=True
            )
            
            service_name = f"{extension_name}_ui"
            self.processes[service_name] = proc
            self.update_service_status(service_name, pid=proc.pid, port=port, status="starting")
            self.log("INFO", f"Started {extension_name} UI with PID {proc.pid} on port {port}")
            
            # Check if process is still running after 1 second and update to running
            import time
            time.sleep(1)
            if proc.poll() is None:  # Process still running
                # Update status only, keep existing pid and port
                if service_name in self.state.get('services', {}):
                    self.state['services'][service_name]['status'] = 'running'
                    self.save_state()
                self.log("INFO", f"{extension_name} UI is running")
                self._reload_caddy_config(reason=f"start-ui:{extension_name}")
            
        except Exception as e:
            self.log("ERROR", f"Failed to start {extension_name} UI: {e}")
            self.log("ERROR", traceback.format_exc())
            self.update_service_status(f"{extension_name}_ui", status="failed")
    
    def _start_extension_service(self, extension_name, service_name, service_path):
        """Start an extension service"""
        try:
            start_script = service_path / "start.sh"
            config_file = service_path / "service_config.json"
            
            if not start_script.exists():
                self.log("WARNING", f"Service {service_name} has no start.sh, skipping")
                return
            
            # Read service config
            service_config = {}
            if config_file.exists():
                with open(config_file, 'r') as f:
                    service_config = json.load(f)
            
            requires_port = service_config.get("requires_port", False)
            service_key = f"{extension_name}.{service_name}"
            
            # Assign port if needed
            port = None
            if requires_port:
                port = self.assign_port("service", service_key, requires_port=True)
            
            # Make start.sh executable
            import os
            os.chmod(start_script, 0o755)
            
            # Set environment variables
            env = os.environ.copy()
            env['LUNA_PORTS'] = json.dumps(self.get_port_mappings())
            
            # Open log file
            log_file = self.logs_path / f"{extension_name}__service_{service_name}.log"
            log_fp = open(log_file, 'w')
            
            # Build command
            cmd = [str(start_script)]
            if port:
                cmd.append(str(port))
            
            # Start the service
            proc = subprocess.Popen(
                cmd,
                stdout=log_fp,
                stderr=subprocess.STDOUT,
                cwd=str(service_path),
                env=env,
                start_new_session=True
            )
            
            full_service_name = f"{extension_name}__service_{service_name}"
            self.processes[full_service_name] = proc
            self.update_service_status(full_service_name, pid=proc.pid, port=port, status="starting")
            self.log("INFO", f"Started service {service_key} with PID {proc.pid}" + (f" on port {port}" if port else ""))
            
            # Check if process is still running after 1 second and update to running
            import time
            time.sleep(1)
            if proc.poll() is None:  # Process still running
                # Update status only, keep existing pid and port
                if full_service_name in self.state.get('services', {}):
                    self.state['services'][full_service_name]['status'] = 'running'
                    self.save_state()
                self.log("INFO", f"Service {service_key} is running")
                self._reload_caddy_config(reason=f"start-service:{service_key}")
            
        except Exception as e:
            self.log("ERROR", f"Failed to start service {extension_name}.{service_name}: {e}")
            self.log("ERROR", traceback.format_exc())
            self.update_service_status(f"{extension_name}__service_{service_name}", status="failed")
    
    def _discover_and_start_extensions(self):
        """Discover enabled extensions and start their UIs and services"""
        self.log("INFO", "Discovering and starting extensions...")
        
        extensions_dir = self.repo_path / "extensions"
        if not extensions_dir.exists():
            self.log("WARNING", "No extensions directory found")
            return
        
        # Get enabled extensions from master config
        enabled_extensions = {
            name: config 
            for name, config in self.master_config.get("extensions", {}).items() 
            if config.get("enabled", False)
        }
        
        self.log("INFO", f"Found {len(enabled_extensions)} enabled extensions")
        
        for extension_name in enabled_extensions:
            extension_path = extensions_dir / extension_name
            
            if not extension_path.exists():
                self.log("WARNING", f"Extension {extension_name} not found at {extension_path}")
                continue
            
            self.log("INFO", f"Processing extension: {extension_name}")
            
            # Start extension UI if it exists
            self._start_extension_ui(extension_name, extension_path)
            
            # Start extension services if they exist
            services_dir = extension_path / "services"
            if services_dir.exists():
                for service_dir in services_dir.iterdir():
                    if service_dir.is_dir():
                        service_name = service_dir.name
                        self.log("INFO", f"Found service: {extension_name}.{service_name}")
                        self._start_extension_service(extension_name, service_name, service_dir)
        
        # Reload Caddy config now that all extensions are started
        self._reload_caddy_config(reason="discover-and-start")
    
    def run_config_sync(self):
        """Run config sync to discover and sync extensions"""
        self.log("INFO", "Running config sync...")
        
        try:
            # Import config_sync module
            import sys
            from pathlib import Path
            
            # Add core/scripts to path
            scripts_path = self.core_path / "scripts"
            if str(scripts_path) not in sys.path:
                sys.path.insert(0, str(scripts_path))
            
            import config_sync
            
            # Run sync
            synced, skipped = config_sync.sync_all(self.repo_path)
            
            self.log("INFO", f"Config sync complete: {len(synced)} synced, {len(skipped)} skipped")
            
            # Reload master config after sync (extensions may have been added)
            self.load_or_create_master_config()
            
        except Exception as e:
            self.log("ERROR", f"Config sync failed: {e}")
            import traceback
            self.log("ERROR", traceback.format_exc())
    
    def startup(self):
        """Main startup flow"""
        self.log("INFO", "=" * 60)
        self.log("INFO", "Luna Supervisor Starting...")
        self.log("INFO", f"Repository path: {self.repo_path}")
        self.log("INFO", "=" * 60)
        
        # Phase 1: Check for update queue
        if self.check_for_update_queue():
            self.log("INFO", "(In full implementation, would process updates here)")
        
        # Phase 2: Load or create master config
        self.load_or_create_master_config()
        
        # Phase 3: Run config sync (discovers new extensions and syncs configs)
        self.run_config_sync()
        
        # Phase 4: Load or create state
        self.load_or_create_state()
        
        # Phase 5: Start core services
        self.log("INFO", "Starting core services...")
        self._start_caddy()
        self._start_hub_ui()
        self._start_agent_api()
        self._start_mcp_server()
        
        # Phase 6: Discover and start extensions
        self._discover_and_start_extensions()
        
        # Phase 7: Load external services into monitoring
        self._load_external_services()
        
        # Phase 8: Start health monitoring thread
        self._start_health_monitoring()
        
        # Phase 9: Startup complete, ready for API
        self.log("INFO", "=" * 60)
        self.log("INFO", "Supervisor startup complete")
        self.log("INFO", f"Master config: {self.master_config_path}")
        self.log("INFO", f"State file: {self.state_path}")
        self.log("INFO", "=" * 60)
        self.log("INFO", "MAIN ACCESS POINT:")
        self.log("INFO", "  Caddy Reverse Proxy: http://0.0.0.0:8443")
        self.log("INFO", "=" * 60)
        self.log("INFO", "Direct service access (localhost only):")
        self.log("INFO", "  Hub UI: http://127.0.0.1:5173")
        self.log("INFO", "  Agent API: http://127.0.0.1:8080")
        self.log("INFO", "  MCP Server: http://127.0.0.1:8765")
        self.log("INFO", "  Supervisor API: http://127.0.0.1:9999")
        self.log("INFO", "=" * 60)
    
    def _load_external_services(self):
        """Load external services registry into state for monitoring"""
        try:
            self.log("INFO", "Loading external services for monitoring...")
            registry = self.external_services_manager.get_registry()
            
            # Initialize external_services in state if not present
            if "external_services" not in self.state:
                self.state["external_services"] = {}
            
            # Add each installed service to state
            for service_name, service_data in registry.items():
                self.state["external_services"][service_name] = {
                    "status": service_data.get("status", "unknown"),
                    "last_check": service_data.get("last_health_check")
                }
            
            self.save_state()
            
            installed_count = len(registry)
            self.log("INFO", f"Loaded {installed_count} external services for monitoring")
            
        except Exception as e:
            self.log("ERROR", f"Failed to load external services: {e}")
            self.log("ERROR", traceback.format_exc())
    
    def _start_health_monitoring(self):
        """Start health monitoring thread for external services"""
        try:
            self.log("INFO", "Starting health monitoring thread...")
            
            def health_monitor_loop():
                import time
                while True:
                    try:
                        time.sleep(30)  # Check every 30 seconds
                        self._health_check_external_services()
                    except Exception as e:
                        self.log("ERROR", f"Health monitoring error: {e}")
            
            health_thread = threading.Thread(target=health_monitor_loop, daemon=True)
            health_thread.start()
            
            self.log("INFO", "Health monitoring thread started")
            
        except Exception as e:
            self.log("ERROR", f"Failed to start health monitoring: {e}")
            self.log("ERROR", traceback.format_exc())
    
    def _health_check_external_services(self):
        """Run health checks for all installed external services"""
        try:
            registry = self.external_services_manager.get_registry()
            
            for service_name in registry.keys():
                try:
                    # Run health check
                    status, error = self.external_services_manager.check_health(service_name)
                    
                    # Update registry
                    self.external_services_manager.update_registry(service_name, {
                        "status": status,
                        "last_health_check": datetime.now().isoformat()
                    })
                    
                    # Update state
                    if "external_services" not in self.state:
                        self.state["external_services"] = {}
                    
                    self.state["external_services"][service_name] = {
                        "status": status,
                        "last_check": datetime.now().isoformat()
                    }
                    
                except Exception as e:
                    self.log("ERROR", f"Health check failed for {service_name}: {e}")
                    
                    # Mark as unknown on error
                    if "external_services" not in self.state:
                        self.state["external_services"] = {}
                    
                    self.state["external_services"][service_name] = {
                        "status": "unknown",
                        "last_check": datetime.now().isoformat()
                    }
            
            # Save state after all checks
            self.save_state()
            
        except Exception as e:
            self.log("ERROR", f"External services health check loop error: {e}")
    
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
