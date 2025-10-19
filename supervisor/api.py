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
    """Initiate restart and update flow"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    import shutil
    import subprocess
    from pathlib import Path
    
    # Copy apply_updates to /tmp
    apply_updates_source = supervisor_instance.repo_path / "core" / "scripts" / "apply_updates.py"
    apply_updates_temp = Path("/tmp/luna_apply_updates.py")
    
    shutil.copy2(apply_updates_source, apply_updates_temp)
    
    # Spawn detached process
    process = subprocess.Popen(
        ["python3", str(apply_updates_temp), str(supervisor_instance.repo_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True
    )
    
    # Schedule supervisor shutdown (allow response to be sent first)
    import threading
    def shutdown_after_delay():
        import time
        time.sleep(1)
        import sys
        sys.exit(0)
    
    thread = threading.Thread(target=shutdown_after_delay)
    thread.daemon = True
    thread.start()
    
    return {"status": "restarting", "message": "System restart initiated"}


@app.post('/shutdown')
def shutdown_system():
    """Gracefully shutdown the entire Luna system"""
    if not supervisor_instance:
        raise HTTPException(status_code=500, detail="Supervisor not initialized")
    
    print("Shutdown requested via API")
    
    # TODO: In full implementation, stop all services gracefully here
    # For now, just exit supervisor which will cause bootstrap to stop
    
    # Create shutdown flag file so bootstrap knows not to restart
    from pathlib import Path
    shutdown_flag = supervisor_instance.repo_path / ".luna_shutdown"
    shutdown_flag.touch()
    print(f"Created shutdown flag at {shutdown_flag}")
    
    # Schedule supervisor shutdown (allow response to be sent first)
    import threading
    import os
    import signal
    def shutdown_after_delay():
        import time
        time.sleep(1)
        print("Shutting down supervisor...")
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

