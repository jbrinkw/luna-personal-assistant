"""
Supervisor API Server
Exposes HTTP endpoints for supervisor control and monitoring
"""
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
from pathlib import Path
from dotenv import load_dotenv, dotenv_values

app = FastAPI(title="Luna Supervisor API")

# Add CORS middleware for network access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for network access
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
                'url': f"http://127.0.0.1:{service_info.get('port')}" if service_info.get('port') else None,
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
    
    # Add synthetic UI status for tool-only extensions (no UI, no services, but have tools)
    import time
    for ext_name, ext_data in extensions_data.items():
        if ext_data.get('ui') is None and not ext_data.get('services') and ext_data.get('tool_count', 0) > 0:
            # Tool-only extension: show as "running" if enabled
            is_enabled = ext_data.get('enabled', True)
            ext_data['ui'] = {
                'status': 'running' if is_enabled else 'offline',
                'port': None,
                'pid': None,
                'url': None,
            }
    
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
        ["python3", str(apply_updates_temp), str(supervisor_instance.repo_path)],
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
        
        print("All services stopped. Shutting down supervisor...")
        print("Bootstrap will restart supervisor after updates complete")
        
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
        
        print("All services stopped. Shutting down supervisor...")
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


def run_api(host='0.0.0.0', port=9999):
    """Run the API server"""
    uvicorn.run(app, host=host, port=port, log_level="info")

