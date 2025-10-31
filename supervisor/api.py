"""
Supervisor API Server
Exposes HTTP endpoints for supervisor control and monitoring
"""
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
from pathlib import Path
from dotenv import load_dotenv, dotenv_values

SUPERVISOR_API_TOKEN = os.getenv("SUPERVISOR_API_TOKEN", "").strip()
_SUPERVISOR_UNPROTECTED_PATHS = {"/health"}

app = FastAPI(title="Luna Supervisor API")

# Add CORS middleware for network access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for network access
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if SUPERVISOR_API_TOKEN:
    @app.middleware("http")
    async def _require_supervisor_token(request: Request, call_next):  # type: ignore
        """Enforce bearer token for supervisor control endpoints when configured."""
        if request.method == "OPTIONS" or request.url.path in _SUPERVISOR_UNPROTECTED_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "missing bearer token"})

        token = auth_header.split(" ", 1)[1].strip()
        if token != SUPERVISOR_API_TOKEN:
            return JSONResponse(status_code=401, content={"detail": "invalid token"})

        return await call_next(request)

# Global references to supervisor state (will be set by supervisor.py)
supervisor_instance = None


class PortAssignRequest(BaseModel):
    type: str  # 'extension' or 'service'
    name: str
    requires_port: bool = True


class ServiceStatusUpdate(BaseModel):
    pid: Optional[int] = None
    port: Optional[int] = None
    status: Optional[str] = None


def _trigger_caddy_reload(reason: str) -> None:
    """Best-effort Caddy reload via supervisor helper."""
    if not supervisor_instance:
        return
    try:
        supervisor_instance.reload_caddy(reason=reason)
    except Exception as exc:  # noqa: BLE001
        print(f"[SupervisorAPI] Warning: Caddy reload failed ({reason}): {exc}", flush=True)


def init_api(supervisor):
    """Initialize API with supervisor instance"""
    global supervisor_instance
    supervisor_instance = supervisor


@app.get('/health')
def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get('/services/status')
def services_status():
    """Get current state.json contents"""
    if supervisor_instance:
        return supervisor_instance.get_state()
    return {"services": {}}


@app.get('/ports')
def get_ports():
    """Get port mapping dictionary"""
    if supervisor_instance:
        return supervisor_instance.get_port_mappings()
    return {"core": {}, "extensions": {}, "services": {}}


@app.get('/extensions')
def get_extensions():
    """Get extensions with UI and services info (for Hub UI)"""
    if not supervisor_instance:
        return {"extensions": []}
    
    # Get state from supervisor
    state = supervisor_instance.get_state()
    services_dict = state.get('services', {})
    
    # Get master config for tool counts and enabled status
    from pathlib import Path
    import json
    master_config_path = Path(supervisor_instance.repo_path) / 'core' / 'master_config.json'
    master_config = {}
    try:
        with open(master_config_path, 'r') as f:
            master_config = json.load(f)
    except:
        pass
    
    # Group by extension
    extensions_data = {}
    
    # Core services to exclude (not extensions)
    CORE_SERVICES = {'hub_ui', 'agent_api', 'mcp_server', 'supervisor'}
    
    for service_key, service_info in services_dict.items():
        # Skip core services
        if service_key in CORE_SERVICES:
            continue
            
        # Parse service key to extract extension name
        if service_key.endswith('_ui'):
            # This is a UI service
            ext_name = service_key.replace('_ui', '')
            if ext_name not in extensions_data:
                extensions_data[ext_name] = {'name': ext_name, 'ui': None, 'services': [], 'tool_count': 0, 'enabled': True}
            extensions_data[ext_name]['ui'] = {
                'status': service_info.get('status'),
                'port': service_info.get('port'),
                'pid': service_info.get('pid'),
                'url': f"/ext/{ext_name}",  # Use Caddy proxy path instead of direct port
            }
        elif '__service_' in service_key:
            # This is an extension service
            parts = service_key.split('__service_')
            ext_name = parts[0]
            service_name = parts[1]
            if ext_name not in extensions_data:
                extensions_data[ext_name] = {'name': ext_name, 'ui': None, 'services': [], 'tool_count': 0, 'enabled': True}
            extensions_data[ext_name]['services'].append({
                'name': service_name,
                'status': service_info.get('status'),
                'port': service_info.get('port'),
                'pid': service_info.get('pid'),
                'requires_port': service_info.get('port') is not None,
            })
    
    # Add tool counts and enabled status from master_config
    # BUT ONLY for extensions that actually exist in the filesystem
    ext_configs = master_config.get('extensions', {})
    extensions_root = Path(supervisor_instance.repo_path) / 'extensions'
    for ext_name in ext_configs.keys():
        # Verify extension directory exists
        ext_path = extensions_root / ext_name
        if not ext_path.exists() or not ext_path.is_dir():
            continue  # Skip extensions that don't exist on disk
        
        if ext_name not in extensions_data:
            extensions_data[ext_name] = {'name': ext_name, 'ui': None, 'services': [], 'tool_count': 0, 'enabled': False}
        extensions_data[ext_name]['enabled'] = ext_configs[ext_name].get('enabled', True)
    
    # Discover tools and version for each extension
    try:
        from core.utils.extension_discovery import discover_extensions
        extensions_root = Path(supervisor_instance.repo_path) / 'extensions'
        discovered_exts = discover_extensions(str(extensions_root))
        for disc_ext in discovered_exts:
            ext_name = disc_ext.get('name', '')
            if ext_name in extensions_data:
                tools = disc_ext.get('tools', [])
                extensions_data[ext_name]['tool_count'] = len(tools)
    except Exception as e:
        print(f"[SupervisorAPI] Warning: Failed to discover tools: {e}", flush=True)
    
    # Add version from each extension's config.json
    for ext_name in list(extensions_data.keys()):
        ext_path = extensions_root / ext_name
        config_path = ext_path / 'config.json'
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    ext_config = json.load(f)
                    extensions_data[ext_name]['version'] = ext_config.get('version', 'unknown')
            except:
                extensions_data[ext_name]['version'] = 'unknown'
        else:
            extensions_data[ext_name]['version'] = 'unknown'
    
    # Don't add synthetic UI for tool-only extensions
    # Only include extensions that actually have a UI or services running
    
    return {"extensions": list(extensions_data.values())}


@app.post('/ports/assign')
def assign_port(request: PortAssignRequest):
    """Assign port to extension or service"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    port = supervisor_instance.assign_port(
        request.type, 
        request.name, 
        request.requires_port
    )
    return {"port": port, "assigned": True}


@app.post('/services/{service_name}/update-status')
def update_service_status(service_name: str, update: ServiceStatusUpdate):
    """Update service status in state.json"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    supervisor_instance.update_service_status(
        service_name, 
        update.pid, 
        update.port, 
        update.status
    )
    return {"updated": True}


@app.post('/config/sync')
def sync_config():
    """Manually trigger config sync"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    # Import config_sync module
    import sys
    from pathlib import Path
    
    # Add core/scripts to path
    scripts_path = supervisor_instance.repo_path / "core" / "scripts"
    if str(scripts_path) not in sys.path:
        sys.path.insert(0, str(scripts_path))
    
    import config_sync
    
    # Run sync
    synced, skipped = config_sync.sync_all(supervisor_instance.repo_path)
    
    return {
        "success": True,
        "synced": synced,
        "skipped": skipped
    }


@app.get('/config/extension/{name}')
def get_extension_config(name: str):
    """Get merged config for an extension"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    ext_path = supervisor_instance.repo_path / "extensions" / name
    config_path = ext_path / "config.json"
    
    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"Extension {name} not found")
    
    import json
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    return config


@app.get('/config/master')
def get_master_config():
    """Returns complete master_config.json"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    if not supervisor_instance.master_config_path.exists():
        raise HTTPException(status_code=404, detail="Master config not found")
    
    return supervisor_instance.master_config


@app.put('/config/master')
def update_master_config(config: Dict[str, Any]):
    """Update entire master config"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    supervisor_instance.master_config = config
    supervisor_instance.save_master_config()
    
    return {"updated": True}


@app.patch('/config/master/extensions/{name}')
def update_extension_in_master(name: str, data: Dict[str, Any]):
    """Update specific extension in master config"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    if "extensions" not in supervisor_instance.master_config:
        supervisor_instance.master_config["extensions"] = {}
    
    if name not in supervisor_instance.master_config["extensions"]:
        supervisor_instance.master_config["extensions"][name] = {}
    
    # Update extension data
    supervisor_instance.master_config["extensions"][name].update(data)
    supervisor_instance.save_master_config()
    
    return {"updated": True}


@app.patch('/config/master/tool/{tool_name}')
def update_tool_config(tool_name: str, config: Dict[str, Any]):
    """Update specific tool config in master"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    if "tool_configs" not in supervisor_instance.master_config:
        supervisor_instance.master_config["tool_configs"] = {}
    
    supervisor_instance.master_config["tool_configs"][tool_name] = config
    supervisor_instance.save_master_config()
    
    return {"updated": True}


@app.get('/queue/current')
def get_queue():
    """Returns current update_queue.json or {"exists": false}"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    queue_path = supervisor_instance.update_queue_path
    
    if not queue_path.exists():
        return {"exists": False}
    
    import json
    with open(queue_path, 'r') as f:
        queue_data = json.load(f)
    
    return queue_data


@app.post('/queue/save')
def save_queue(queue: Dict[str, Any]):
    """Save queue to update_queue.json"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    queue_path = supervisor_instance.update_queue_path
    
    import json
    with open(queue_path, 'w') as f:
        json.dump(queue, f, indent=2)
    
    return {"saved": True}


@app.delete('/queue/current')
def delete_queue():
    """Delete update_queue.json"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    queue_path = supervisor_instance.update_queue_path
    
    if queue_path.exists():
        queue_path.unlink()
    
    return {"deleted": True}


@app.get('/queue/status')
def queue_status():
    """Get queue summary"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    queue_path = supervisor_instance.update_queue_path
    
    if not queue_path.exists():
        return {
            "exists": False,
            "operation_count": 0,
            "operations": []
        }
    
    import json
    with open(queue_path, 'r') as f:
        queue_data = json.load(f)
    
    operations = queue_data.get("operations", [])
    
    return {
        "exists": True,
        "operation_count": len(operations),
        "operations": operations
    }


@app.post('/core/check-updates')
def check_core_updates():
    """Check for Luna core updates from git repository"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    import subprocess
    import json
    from pathlib import Path
    
    # Path to check_core_updates script
    check_script = supervisor_instance.repo_path / "core" / "scripts" / "check_core_updates.py"
    
    if not check_script.exists():
        raise HTTPException(status_code=500, detail="Update check script not found")
    
    try:
        # Run the check script
        result = subprocess.run(
            [supervisor_instance.python_bin, str(check_script), str(supervisor_instance.repo_path)],
            capture_output=True,
            text=True,
            cwd=str(supervisor_instance.repo_path),
            timeout=30
        )
        
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Update check failed: {result.stderr}")
        
        # Parse JSON output
        update_info = json.loads(result.stdout)
        
        return update_info
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Update check timed out")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse update check result: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update check failed: {str(e)}")


@app.post('/api/extensions/install-dependencies')
def install_dependencies():
    """Run Phase 6 dependency installation without restart"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    # Import apply_updates module
    import sys
    from pathlib import Path
    
    scripts_path = supervisor_instance.repo_path / "core" / "scripts"
    if str(scripts_path) not in sys.path:
        sys.path.insert(0, str(scripts_path))
    
    import apply_updates
    
    try:
        # Run dependency installation
        apply_updates.phase_6_install_dependencies(supervisor_instance.repo_path)
        return {"success": True, "message": "Dependencies installed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dependency installation failed: {str(e)}")


@app.post('/restart')
def restart_system():
    """Initiate restart and update flow with graceful shutdown"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")

    print("Restart requested via API")
    _trigger_caddy_reload("api-restart-requested")
    
    import shutil
    import subprocess
    from pathlib import Path
    
    # Create update flag FIRST to signal bootstrap to wait
    update_flag = supervisor_instance.repo_path / ".luna_updating"
    update_flag.touch()
    print(f"Created update flag at {update_flag}")
    
    # Copy apply_updates to /tmp
    apply_updates_source = supervisor_instance.repo_path / "core" / "scripts" / "apply_updates.py"
    apply_updates_temp = Path("/tmp/luna_apply_updates.py")
    
    shutil.copy2(apply_updates_source, apply_updates_temp)
    print(f"Copied apply_updates to {apply_updates_temp}")
    
    # Open log file for apply_updates output
    logs_path = supervisor_instance.repo_path / "logs"
    logs_path.mkdir(parents=True, exist_ok=True)
    apply_updates_log = logs_path / "apply_updates.log"
    log_fp = open(apply_updates_log, 'a')
    
    # Spawn detached process with output redirected to log
    process = subprocess.Popen(
        [supervisor_instance.python_bin, str(apply_updates_temp), str(supervisor_instance.repo_path)],
        stdout=log_fp,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True
    )
    
    print(f"Spawned apply_updates process (PID: {process.pid})")
    print(f"Output redirected to {apply_updates_log}")
    
    # Schedule graceful shutdown (allow response to be sent first)
    import threading
    import os
    import signal
    def shutdown_after_delay():
        import time
        import subprocess
        time.sleep(1)
        
        # Stop all tracked processes and their entire process groups
        print("Shutting down all services before update...")
        for service_name, proc in supervisor_instance.processes.items():
            if proc and proc.poll() is None:  # Process still running
                print(f"Stopping {service_name} (PID: {proc.pid})")
                try:
                    # Kill entire process group (negative PID)
                    pgid = os.getpgid(proc.pid)
                    print(f"  Killing process group {pgid}")
                    os.killpg(pgid, signal.SIGTERM)  # Send SIGTERM to whole group
                    time.sleep(0.5)
                    
                    # Check if process is still running
                    if proc.poll() is None:
                        print(f"  Force killing process group {pgid}")
                        os.killpg(pgid, signal.SIGKILL)  # Force kill if needed
                except ProcessLookupError:
                    print(f"  Process group already terminated")
                except Exception as e:
                    print(f"  Error stopping {service_name}: {e}")
                    # Fallback to individual process kill
                    try:
                        proc.terminate()
                        time.sleep(0.5)
                        if proc.poll() is None:
                            proc.kill()
                    except:
                        pass
        
        # Kill processes on core Luna ports and verify they're gone
        print("Checking core Luna ports...")
        for port in [5173, 8080, 8765, 9999]:
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True)
                    if result.stdout.strip():
                        pids = result.stdout.strip().split('\n')
                        for pid in pids:
                            if pid:
                                print(f"Killing process on port {port} (PID: {pid}, attempt {attempt + 1}/{max_retries})")
                                try:
                                    os.kill(int(pid), signal.SIGKILL)
                                except:
                                    pass
                        time.sleep(0.3)  # Wait for process to fully die and release port
                    else:
                        # Port is clear
                        print(f"Port {port} cleared")
                        break
                except:
                    break
        
        # Kill processes on extension UI ports (5200-5299) and service ports (5300-5399)
        print("Checking extension UI and service ports...")
        for port in range(5200, 5400):
            try:
                result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True)
                if result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid:
                            print(f"Killing process on port {port} (PID: {pid})")
                            try:
                                os.kill(int(pid), signal.SIGKILL)
                            except:
                                pass
                    time.sleep(0.2)  # Brief wait to ensure port release
            except:
                pass
        
        # Kill Caddy but preserve ngrok tunnel across restarts
        print("Stopping Caddy (preserving ngrok tunnel)...")
        try:
            subprocess.run(['pkill', '-9', '-f', 'caddy run'], capture_output=True)
        except:
            pass
        
        print("All services stopped. Shutting down supervisor...")
        print("Bootstrap will restart supervisor after updates complete")
        print("(ngrok tunnel preserved for continuity)")
        _trigger_caddy_reload("api-restart-shutdown")
        
        # Send SIGTERM to our own process - uvicorn will handle it gracefully
        os.kill(os.getpid(), signal.SIGTERM)
    
    thread = threading.Thread(target=shutdown_after_delay)
    thread.daemon = True
    thread.start()
    
    return {"status": "restarting", "message": "System restart and update initiated"}


@app.post('/shutdown')
def shutdown_system():
    """Gracefully shutdown the entire Luna system"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    print("Shutdown requested via API")
    _trigger_caddy_reload("api-shutdown-requested")
    
    # Create shutdown flag file so bootstrap knows not to restart
    from pathlib import Path
    shutdown_flag = supervisor_instance.repo_path / ".luna_shutdown"
    shutdown_flag.touch()
    print(f"Created shutdown flag at {shutdown_flag}")
    
    # Schedule supervisor shutdown (allow response to be sent first)
    import threading
    import os
    import signal
    import subprocess
    def shutdown_after_delay():
        import time
        import subprocess
        time.sleep(1)
        
        # Stop all tracked processes and their entire process groups
        print("Shutting down all services...")
        for service_name, process in supervisor_instance.processes.items():
            if process and process.poll() is None:  # Process still running
                print(f"Stopping {service_name} (PID: {process.pid})")
                try:
                    # Kill entire process group (negative PID)
                    # This kills the process and all its children
                    pgid = os.getpgid(process.pid)
                    print(f"  Killing process group {pgid}")
                    os.killpg(pgid, signal.SIGTERM)  # Send SIGTERM to whole group
                    time.sleep(0.5)
                    
                    # Check if process is still running
                    if process.poll() is None:
                        print(f"  Force killing process group {pgid}")
                        os.killpg(pgid, signal.SIGKILL)  # Force kill if needed
                except ProcessLookupError:
                    print(f"  Process group already terminated")
                except Exception as e:
                    print(f"  Error stopping {service_name}: {e}")
                    # Fallback to individual process kill
                    try:
                        process.terminate()
                        time.sleep(0.5)
                        if process.poll() is None:
                            process.kill()
                    except:
                        pass
        
        # Kill processes on core Luna ports and verify they're gone
        print("Checking core Luna ports...")
        for port in [5173, 8080, 8765, 9999]:
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True)
                    if result.stdout.strip():
                        pids = result.stdout.strip().split('\n')
                        for pid in pids:
                            if pid:
                                print(f"Killing process on port {port} (PID: {pid}, attempt {attempt + 1}/{max_retries})")
                                try:
                                    os.kill(int(pid), signal.SIGKILL)
                                except:
                                    pass
                        time.sleep(0.3)  # Wait for process to fully die and release port
                    else:
                        # Port is clear
                        print(f"Port {port} cleared")
                        break
                except:
                    break
        
        # Kill processes on extension UI ports (5200-5299) and service ports (5300-5399)
        print("Checking extension UI and service ports...")
        for port in range(5200, 5400):
            try:
                result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True)
                if result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid:
                            print(f"Killing process on port {port} (PID: {pid})")
                            try:
                                os.kill(int(pid), signal.SIGKILL)
                            except:
                                pass
                    time.sleep(0.2)  # Brief wait to ensure port release
            except:
                pass
        
        # Kill Caddy and ngrok (full shutdown)
        print("Stopping Caddy and ngrok...")
        try:
            subprocess.run(['pkill', '-9', '-f', 'caddy run'], capture_output=True)
            subprocess.run(['pkill', '-9', '-f', 'ngrok http'], capture_output=True)
        except:
            pass
        
        print("All services stopped. Shutting down supervisor...")
        _trigger_caddy_reload("api-shutdown-thread")
        # Send SIGTERM to our own process - uvicorn will handle it gracefully
        os.kill(os.getpid(), signal.SIGTERM)
    
    thread = threading.Thread(target=shutdown_after_delay)
    thread.daemon = True
    thread.start()
    
    return {"status": "shutting_down", "message": "Luna system shutdown initiated"}


def get_env_path():
    """Get the path to the .env file"""
    if supervisor_instance:
        return supervisor_instance.repo_path / ".env"
    # Fallback to current directory
    return Path(".env")


def read_env_file():
    """Read .env file and return dict of key-value pairs"""
    env_path = get_env_path()
    if not env_path.exists():
        return {}
    return dotenv_values(str(env_path))


def write_env_file(env_dict):
    """Write dict of key-value pairs to .env file"""
    env_path = get_env_path()
    lines = [f"{key}={value}" for key, value in sorted(env_dict.items())]
    env_path.write_text('\n'.join(lines) + '\n')
    # Hot reload
    load_dotenv(str(env_path), override=True)


@app.get('/keys/list')
def list_keys():
    """List all keys from .env file (values masked)"""
    env_dict = read_env_file()
    return env_dict


@app.post('/keys/set')
def set_key(data: Dict[str, str]):
    """Set or update a key in .env file"""
    key = data.get('key')
    value = data.get('value')
    
    if not key:
        raise HTTPException(status_code=400, detail="Key is required")
    
    env_dict = read_env_file()
    env_dict[key] = value
    write_env_file(env_dict)
    
    return {"status": "updated", "key": key}


@app.post('/keys/delete')
def delete_key(data: Dict[str, str]):
    """Delete a key from .env file"""
    key = data.get('key')
    
    if not key:
        raise HTTPException(status_code=400, detail="Key is required")
    
    env_dict = read_env_file()
    if key in env_dict:
        del env_dict[key]
        write_env_file(env_dict)
    
    return {"status": "deleted", "key": key}


@app.post('/keys/upload-env')
async def upload_env(file: UploadFile = File(...)):
    """Upload and merge .env file"""
    try:
        # Read uploaded file
        contents = await file.read()
        uploaded_env = {}
        
        for line in contents.decode('utf-8').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                uploaded_env[key.strip()] = value.strip()
        
        # Merge with existing
        env_dict = read_env_file()
        env_dict.update(uploaded_env)
        write_env_file(env_dict)
        
        return {"updated_count": len(uploaded_env)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process .env file: {str(e)}")


@app.get('/keys/required')
def get_required_keys():
    """Get required keys from all extensions"""
    if not supervisor_instance:
        return {}
    
    required = {}
    ext_path = supervisor_instance.repo_path / "extensions"
    
    if ext_path.exists():
        import json
        for ext_dir in ext_path.iterdir():
            if ext_dir.is_dir():
                config_path = ext_dir / "config.json"
                if config_path.exists():
                    try:
                        with open(config_path, 'r') as f:
                            config = json.load(f)
                            if 'required_secrets' in config:
                                for secret in config['required_secrets']:
                                    if secret not in required:
                                        required[secret] = []
                                    required[secret].append(ext_dir.name)
                    except Exception as e:
                        print(f"Error reading {config_path}: {e}")
    
    return required


# ============================================================================
# Tools API Endpoints
# ============================================================================

@app.get('/tools/discover')
def discover_tools(extension: Optional[str] = None):
    """Discover tools from all extensions or a specific extension.
    
    Args:
        extension: Optional extension name to filter by
        
    Returns:
        {
            "tools": [
                {
                    "name": str,
                    "description": str,
                    "extension": str,
                    "parameters": dict (if available from function signature)
                }
            ]
        }
    """
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    try:
        from core.utils.extension_discovery import discover_extensions
        from pathlib import Path
        import inspect
        
        extensions_root = Path(supervisor_instance.repo_path) / 'extensions'
        discovered_exts = discover_extensions(str(extensions_root))
        
        tools_list = []
        
        for ext in discovered_exts:
            ext_name = ext.get('name', '')
            
            # Filter by extension if specified
            if extension and ext_name != extension:
                continue
            
            tools = ext.get('tools', [])
            tool_configs = ext.get('tool_configs', {})
            
            for tool in tools:
                if not callable(tool):
                    continue
                
                tool_name = tool.__name__
                tool_doc = tool.__doc__ or "No description available"
                
                # Extract first line of docstring as description
                description = tool_doc.strip().split('\n')[0] if tool_doc else "No description available"
                
                # Try to get function signature for parameters
                parameters = {}
                try:
                    sig = inspect.signature(tool)
                    parameters = {
                        param_name: {
                            "annotation": str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any",
                            "default": str(param.default) if param.default != inspect.Parameter.empty else None
                        }
                        for param_name, param in sig.parameters.items()
                    }
                except Exception:
                    pass
                
                tools_list.append({
                    "name": tool_name,
                    "description": description,
                    "extension": ext_name,
                    "parameters": parameters,
                    "config": tool_configs.get(tool_name, {})
                })
        
        return {"tools": tools_list}
    except Exception as e:
        print(f"[SupervisorAPI] Error discovering tools: {e}", flush=True)
        raise HTTPException(status_code=500, detail=f"Failed to discover tools: {str(e)}")


@app.get('/tools/list')
def list_tools(extension: Optional[str] = None, enabled_only: bool = False):
    """List all tools with their configurations from master_config.
    
    Args:
        extension: Optional extension name to filter by
        enabled_only: If true, only return tools enabled in MCP
        
    Returns:
        {
            "tools": [
                {
                    "name": str,
                    "extension": str,
                    "config": {
                        "enabled_in_mcp": bool,
                        "passthrough": bool
                    }
                }
            ]
        }
    """
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    try:
        from core.utils.extension_discovery import discover_extensions
        from pathlib import Path
        
        extensions_root = Path(supervisor_instance.repo_path) / 'extensions'
        discovered_exts = discover_extensions(str(extensions_root))
        
        # Get tool configs from master_config
        tool_configs = supervisor_instance.master_config.get('tool_configs', {})
        
        tools_list = []
        
        for ext in discovered_exts:
            ext_name = ext.get('name', '')
            
            # Filter by extension if specified
            if extension and ext_name != extension:
                continue
            
            tools = ext.get('tools', [])
            
            for tool in tools:
                if not callable(tool):
                    continue
                
                tool_name = tool.__name__
                tool_config = tool_configs.get(tool_name, {})
                
                # Default values if not in master_config
                enabled_in_mcp = tool_config.get('enabled_in_mcp', True)
                
                # Filter by enabled status if requested
                if enabled_only and not enabled_in_mcp:
                    continue
                
                tools_list.append({
                    "name": tool_name,
                    "extension": ext_name,
                    "config": {
                        "enabled_in_mcp": enabled_in_mcp,
                        "passthrough": tool_config.get('passthrough', False)
                    }
                })
        
        return {"tools": tools_list}
    except Exception as e:
        print(f"[SupervisorAPI] Error listing tools: {e}", flush=True)
        raise HTTPException(status_code=500, detail=f"Failed to list tools: {str(e)}")


@app.post('/tools/validate/{tool_name}')
def validate_tool(tool_name: str, args: Dict[str, Any]):
    """Validate arguments for a tool without executing it.
    
    Args:
        tool_name: Name of the tool to validate
        args: Arguments to validate
        
    Returns:
        {
            "valid": bool,
            "errors": List[str] (if invalid)
        }
    """
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    try:
        from core.utils.extension_discovery import discover_extensions
        from pathlib import Path
        import inspect
        
        extensions_root = Path(supervisor_instance.repo_path) / 'extensions'
        discovered_exts = discover_extensions(str(extensions_root))
        
        # Find the tool
        tool_func = None
        for ext in discovered_exts:
            for tool in ext.get('tools', []):
                if callable(tool) and tool.__name__ == tool_name:
                    tool_func = tool
                    break
            if tool_func:
                break
        
        if not tool_func:
            raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")
        
        # Validate arguments against function signature
        errors = []
        try:
            sig = inspect.signature(tool_func)
            
            # Check for missing required parameters
            for param_name, param in sig.parameters.items():
                if param.default == inspect.Parameter.empty and param_name not in args:
                    errors.append(f"Missing required parameter: {param_name}")
            
            # Check for unexpected parameters
            valid_params = set(sig.parameters.keys())
            provided_params = set(args.keys())
            unexpected = provided_params - valid_params
            if unexpected:
                errors.append(f"Unexpected parameters: {', '.join(unexpected)}")
        
        except Exception as e:
            errors.append(f"Signature validation error: {str(e)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors if errors else None
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[SupervisorAPI] Error validating tool: {e}", flush=True)
        raise HTTPException(status_code=500, detail=f"Failed to validate tool: {str(e)}")


@app.post('/tools/execute/{tool_name}')
def execute_tool(tool_name: str, args: Dict[str, Any]):
    """Execute a tool with given arguments.
    
    Args:
        tool_name: Name of the tool to execute
        args: Arguments to pass to the tool
        
    Returns:
        {
            "success": bool,
            "result": Any,
            "error": str (if failed)
        }
    """
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    try:
        from core.utils.extension_discovery import discover_extensions
        from pathlib import Path
        
        extensions_root = Path(supervisor_instance.repo_path) / 'extensions'
        discovered_exts = discover_extensions(str(extensions_root))
        
        # Find the tool
        tool_func = None
        for ext in discovered_exts:
            for tool in ext.get('tools', []):
                if callable(tool) and tool.__name__ == tool_name:
                    tool_func = tool
                    break
            if tool_func:
                break
        
        if not tool_func:
            raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")
        
        # Execute the tool
        try:
            result = tool_func(**args)
            
            # Handle different return formats
            # Most Luna tools return (bool, str) tuples
            if isinstance(result, tuple) and len(result) == 2:
                success, output = result
                return {
                    "success": success,
                    "result": output
                }
            else:
                return {
                    "success": True,
                    "result": result
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[SupervisorAPI] Error executing tool: {e}", flush=True)
        raise HTTPException(status_code=500, detail=f"Failed to execute tool: {str(e)}")


# ============================================================================
# External Services API Endpoints
# ============================================================================

class ServiceInstallRequest(BaseModel):
    config: Dict[str, Any]


class ServiceUninstallRequest(BaseModel):
    remove_data: bool = True


class ServiceStatusResponse(BaseModel):
    status: str
    enabled: bool
    last_check: Optional[str]
    ui: Optional[Dict[str, Any]] = None


class ServiceUploadRequest(BaseModel):
    service_definition: Dict[str, Any]


@app.get('/api/external-services/available')
def get_available_external_services():
    """Get list of all available service definitions from external_services/"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    try:
        services = supervisor_instance.external_services_manager.discover_available_services()
        return {"services": services}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to discover services: {str(e)}")


@app.get('/api/external-services/installed')
def get_installed_external_services():
    """Get registry contents with current statuses"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    try:
        registry = supervisor_instance.external_services_manager.get_registry()
        return registry
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get installed services: {str(e)}")


@app.get('/api/external-services/{name}')
def get_external_service_details(name: str):
    """Get service definition + config form + installation status + saved config"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    try:
        # Get service definition
        service_def = supervisor_instance.external_services_manager.get_service_definition(name)
        if not service_def:
            raise HTTPException(status_code=404, detail=f"Service {name} not found")
        
        # Get config form
        config_form = supervisor_instance.external_services_manager.get_config_form(name)
        
        # Check if installed
        registry = supervisor_instance.external_services_manager.get_registry()
        is_installed = name in registry
        ui_routes = supervisor_instance.external_services_manager.get_ui_routes()
        ui_metadata = ui_routes.get(name)
        
        # Get saved config if installed
        saved_config = None
        if is_installed:
            saved_config = supervisor_instance.external_services_manager.get_service_config(name)
        
        return {
            "definition": service_def.dict(),
            "form": config_form.dict() if config_form else {"fields": []},
            "installed": is_installed,
            "config": saved_config,
            "registry_entry": registry.get(name) if is_installed else None,
            "ui_route": ui_metadata
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get service details: {str(e)}")


@app.post('/api/external-services/{name}/install')
def install_external_service(name: str, request: ServiceInstallRequest):
    """Install a service with given configuration"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    try:
        # Validate service exists
        service_def = supervisor_instance.external_services_manager.get_service_definition(name)
        if not service_def:
            raise HTTPException(status_code=404, detail=f"Service {name} not found")
        
        # Install service
        success, message, env_assignments = supervisor_instance.external_services_manager.install_service(
            name,
            request.config
        )
        
        if not success:
            raise HTTPException(status_code=500, detail=message)
        
        # Get saved config to return
        saved_config = supervisor_instance.external_services_manager.get_service_config(name)
        
        # Update supervisor state
        supervisor_instance._load_external_services()
        ui_routes = supervisor_instance.external_services_manager.get_ui_routes()
        ui_metadata = ui_routes.get(name)
        
        return {
            "success": True,
            "message": message,
            "config": saved_config,
            "env_assignments": env_assignments,
            "ui_route": ui_metadata
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Installation failed: {str(e)}")


@app.post('/api/external-services/{name}/uninstall')
def uninstall_external_service(name: str, request: ServiceUninstallRequest):
    """Uninstall a service"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    try:
        success, message = supervisor_instance.external_services_manager.uninstall_service(
            name,
            request.remove_data
        )
        
        if not success:
            raise HTTPException(status_code=500, detail=message)
        
        # Update supervisor state
        supervisor_instance._load_external_services()
        
        return {
            "success": True,
            "message": message
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Uninstallation failed: {str(e)}")


@app.post('/api/external-services/{name}/start')
def start_external_service(name: str):
    """Start a service"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    try:
        success, message = supervisor_instance.external_services_manager.start_service(name)
        
        if not success:
            raise HTTPException(status_code=500, detail=message)
        
        # Get updated status
        registry = supervisor_instance.external_services_manager.get_registry()
        service_data = registry.get(name, {})

        _trigger_caddy_reload(f"external-service-start:{name}")
        
        return {
            "success": True,
            "message": message,
            "status": service_data.get("status", "unknown")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Start failed: {str(e)}")


@app.post('/api/external-services/{name}/stop')
def stop_external_service(name: str):
    """Stop a service"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    try:
        success, message = supervisor_instance.external_services_manager.stop_service(name)
        
        if not success:
            raise HTTPException(status_code=500, detail=message)

        _trigger_caddy_reload(f"external-service-stop:{name}")
        return {
            "success": True,
            "message": message,
            "status": "stopped"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stop failed: {str(e)}")


@app.post('/api/external-services/{name}/restart')
def restart_external_service(name: str):
    """Restart a service"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    try:
        success, message = supervisor_instance.external_services_manager.restart_service(name)
        
        if not success:
            raise HTTPException(status_code=500, detail=message)

        # Get updated status
        registry = supervisor_instance.external_services_manager.get_registry()
        service_data = registry.get(name, {})

        _trigger_caddy_reload(f"external-service-restart:{name}")
        return {
            "success": True,
            "message": message,
            "status": service_data.get("status", "unknown")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restart failed: {str(e)}")


@app.post('/api/external-services/{name}/enable')
def enable_external_service_startup(name: str):
    """Enable auto-start on boot"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    try:
        success, message = supervisor_instance.external_services_manager.enable_startup(name)
        
        if not success:
            raise HTTPException(status_code=500, detail=message)
        
        return {
            "success": True,
            "message": message,
            "enabled": True
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enable failed: {str(e)}")


@app.post('/api/external-services/{name}/disable')
def disable_external_service_startup(name: str):
    """Disable auto-start on boot"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    try:
        success, message = supervisor_instance.external_services_manager.disable_startup(name)
        
        if not success:
            raise HTTPException(status_code=500, detail=message)
        
        return {
            "success": True,
            "message": message,
            "enabled": False
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Disable failed: {str(e)}")


@app.get('/api/external-services/{name}/status')
def get_external_service_status(name: str):
    """Get current status from state.json and registry"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    try:
        registry = supervisor_instance.external_services_manager.get_registry()
        
        if name not in registry:
            raise HTTPException(status_code=404, detail=f"Service {name} not installed")
        
        service_data = registry[name]
        
        return {
            "status": service_data.get("status", "unknown"),
            "enabled": service_data.get("enabled", False),
            "last_check": service_data.get("last_health_check"),
            "ui": service_data.get("ui")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@app.get('/api/external-services/{name}/logs')
def get_external_service_logs(name: str, lines: int = 100):
    """Get last N lines from service log file"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    try:
        log_content = supervisor_instance.external_services_manager.tail_log(name, lines)
        log_path = supervisor_instance.external_services_manager.get_log_path(name)
        
        return {
            "logs": log_content,
            "path": str(log_path)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {str(e)}")


@app.post('/api/external-services/upload')
def upload_external_service(request: ServiceUploadRequest):
    """Upload a new external service definition"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    try:
        # Upload service
        success, message = supervisor_instance.external_services_manager.upload_service(
            request.service_definition
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        return {
            "success": True,
            "message": message,
            "name": request.service_definition.get("name")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload service: {str(e)}")


# ============================================================================
# Remote MCP Server Management Endpoints
# ============================================================================

class AddMCPServerRequest(BaseModel):
    url: str


class MCPServerUpdate(BaseModel):
    enabled: Optional[bool] = None
    tool_updates: Optional[Dict[str, Dict[str, bool]]] = None  # tool_name -> {enabled: bool}


@app.post('/remote-mcp/add')
async def add_remote_mcp_server(request: AddMCPServerRequest):
    """Add or update remote MCP server by URL"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    try:
        import asyncio
        from core.utils.remote_mcp_loader import async_add_or_update_server_from_url
        
        # Load server from URL
        server_entry = await async_add_or_update_server_from_url(
            supervisor_instance.master_config,
            request.url
        )
        
        # Save master config
        supervisor_instance.save_master_config()
        
        return {
            "success": True,
            "message": f"Successfully added/updated server: {server_entry['server_id']}",
            "server": server_entry
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to add MCP server: {str(e)}")


@app.get('/remote-mcp/list')
def list_remote_mcp_servers():
    """List all remote MCP servers"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    remote_servers = supervisor_instance.master_config.get('remote_mcp_servers', {})
    return {"servers": remote_servers}


@app.delete('/remote-mcp/{server_id}')
def remove_remote_mcp_server(server_id: str):
    """Remove a remote MCP server"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    try:
        from core.utils.remote_mcp_loader import remove_server
        
        # Remove from config
        removed = remove_server(supervisor_instance.master_config, server_id)
        
        if not removed:
            raise HTTPException(status_code=404, detail=f"Server not found: {server_id}")
        
        # Save master config
        supervisor_instance.save_master_config()
        
        return {
            "success": True,
            "message": f"Successfully removed server: {server_id}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove server: {str(e)}")


@app.patch('/remote-mcp/{server_id}')
def update_remote_mcp_server(server_id: str, update: MCPServerUpdate):
    """Update server or tool enabled status"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    try:
        remote_servers = supervisor_instance.master_config.get('remote_mcp_servers', {})
        
        if server_id not in remote_servers:
            raise HTTPException(status_code=404, detail=f"Server not found: {server_id}")
        
        server_config = remote_servers[server_id]
        
        # Update server-level enabled status
        if update.enabled is not None:
            server_config['enabled'] = update.enabled
        
        # Update tool-level enabled status
        if update.tool_updates:
            for tool_name, tool_update in update.tool_updates.items():
                if tool_name in server_config.get('tools', {}):
                    if 'enabled' in tool_update:
                        server_config['tools'][tool_name]['enabled'] = tool_update['enabled']
        
        # Save master config
        supervisor_instance.save_master_config()
        
        return {
            "success": True,
            "message": f"Successfully updated server: {server_id}",
            "server": server_config
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update server: {str(e)}")


@app.get('/tools/all')
def get_all_tools():
    """Get all tools from all sources (extensions and remote MCP servers)"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    try:
        from core.utils.tool_discovery import get_all_tools
        
        all_tools = get_all_tools()
        
        return all_tools
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to get tools: {str(e)}")


def run_api(host='127.0.0.1', port=9999):
    """Run the API server"""
    uvicorn.run(app, host=host, port=port, log_level="info")
