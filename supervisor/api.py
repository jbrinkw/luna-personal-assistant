"""
Supervisor API Server
Exposes HTTP endpoints for supervisor control and monitoring
"""
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

app = FastAPI(title="Luna Supervisor API")

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


def run_api(host='127.0.0.1', port=9999):
    """Run the API server"""
    uvicorn.run(app, host=host, port=port, log_level="info")

