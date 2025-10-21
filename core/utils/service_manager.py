"""Service Manager for Luna Extensions

Auto-discovers and auto-starts extension UIs and services, assigns ports,
monitors health, and restarts on failure when configured.

Ports:
- UIs: 5200–5299
- Services: 5300–5399

All processes bind to 0.0.0.0 (network accessible).
"""
import os
import sys
import json
import time
import socket
import threading
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import shutil

# Ensure project root on path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load .env if available
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=str(PROJECT_ROOT / '.env'))
except Exception:
    pass


UI_PORT_START = 5200
UI_PORT_END = 5299
SVC_PORT_START = 5300
SVC_PORT_END = 5399


def _is_port_free(port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.25)
    try:
        return s.connect_ex(("0.0.0.0", port)) != 0
    finally:
        try:
            s.close()
        except Exception:
            pass


def _ensure_logs_dir() -> Path:
    logs = PROJECT_ROOT / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    return logs


class ServiceManager:
    """Manages discovery, startup, and monitoring of extension UIs and services."""

    def __init__(self, extensions_root: Optional[str] = None) -> None:
        self.extensions_root = (
            str(PROJECT_ROOT / 'extensions') if not extensions_root else str(Path(extensions_root).resolve())
        )
        self._lock = threading.RLock()
        self._ui_next_port = UI_PORT_START
        self._svc_next_port = SVC_PORT_START
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Registries
        # key: ext_name
        self._uis: Dict[str, Dict[str, Any]] = {}
        # key: (ext_name, service_name)
        self._services: Dict[Tuple[str, str], Dict[str, Any]] = {}
        
    def _load_master_config(self) -> Dict[str, Any]:
        """Load master_config.json to check enabled state."""
        master_config_path = PROJECT_ROOT / 'core' / 'master_config.json'
        try:
            if master_config_path.exists():
                with open(master_config_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[ServiceManager] Warning: Failed to load master_config: {e}", flush=True)
        return {"extensions": {}}
    
    def _is_extension_enabled(self, ext_name: str) -> bool:
        """Check if extension is enabled in master_config."""
        config = self._load_master_config()
        ext_config = config.get("extensions", {}).get(ext_name, {})
        enabled = ext_config.get("enabled", True)  # Default to True if not specified
        return enabled

    # ---------- Discovery ----------
    def _discover_extensions(self) -> List[str]:
        if not os.path.isdir(self.extensions_root):
            return []
        names: List[str] = []
        for entry in os.listdir(self.extensions_root):
            path = os.path.join(self.extensions_root, entry)
            if os.path.isdir(path):
                names.append(entry)
        return names

    def _discover_ui(self, ext_name: str) -> Optional[Dict[str, Any]]:
        ui_dir = os.path.join(self.extensions_root, ext_name, 'ui')
        start_sh = os.path.join(ui_dir, 'start.sh')
        if os.path.isdir(ui_dir) and os.path.isfile(start_sh):
            return {
                'ext': ext_name,
                'path': ui_dir,
                'start': start_sh,
                'status': 'stopped',
                'port': None,
                'pid': None,
                'last_check': None,
            }
        return None

    def _discover_services(self, ext_name: str) -> List[Dict[str, Any]]:
        services_dir = os.path.join(self.extensions_root, ext_name, 'services')
        results: List[Dict[str, Any]] = []
        if not os.path.isdir(services_dir):
            return results

        for svc_name in os.listdir(services_dir):
            svc_dir = os.path.join(services_dir, svc_name)
            if not os.path.isdir(svc_dir):
                continue
            start_sh = os.path.join(svc_dir, 'start.sh')
            cfg_path = os.path.join(svc_dir, 'service_config.json')
            if not os.path.isfile(start_sh) or not os.path.isfile(cfg_path):
                continue
            cfg: Dict[str, Any] = {}
            try:
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
            except Exception:
                cfg = {}
            requires_port = bool(cfg.get('requires_port', False))
            fixed_port = cfg.get('fixed_port')
            results.append({
                'ext': ext_name,
                'name': cfg.get('name') or svc_name,
                'path': svc_dir,
                'start': start_sh,
                'config': cfg,
                'requires_port': requires_port,
                'fixed_port': fixed_port,
                'status': 'stopped',
                'port': fixed_port if fixed_port and not requires_port else None,
                'pid': None,
                'last_check': None,
            })
        return results

    # ---------- Port allocation ----------
    def _alloc_ui_port(self) -> Optional[int]:
        with self._lock:
            for port in range(self._ui_next_port, UI_PORT_END + 1):
                if _is_port_free(port):
                    self._ui_next_port = port + 1
                    return port
            # wrap once
            for port in range(UI_PORT_START, self._ui_next_port):
                if _is_port_free(port):
                    self._ui_next_port = port + 1
                    return port
            return None

    def _alloc_svc_port(self) -> Optional[int]:
        with self._lock:
            for port in range(self._svc_next_port, SVC_PORT_END + 1):
                if _is_port_free(port):
                    self._svc_next_port = port + 1
                    return port
            for port in range(SVC_PORT_START, self._svc_next_port):
                if _is_port_free(port):
                    self._svc_next_port = port + 1
                    return port
            return None

    # ---------- Process control ----------
    def _popen(self, cmd: List[str], cwd: Optional[str], log_file: Path, env: Optional[Dict[str, str]] = None) -> Optional[subprocess.Popen]:
        try:
            log_fp = open(log_file, 'a', encoding='utf-8')
        except Exception:
            log_fp = open(os.devnull, 'w')  # type: ignore
        try:
            final_env = os.environ.copy()
            if env:
                final_env.update(env)
            proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=log_fp,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env=final_env,
            )
            return proc
        except Exception:
            try:
                log_fp.close()
            except Exception:
                pass
            return None

    def _start_ui(self, ui: Dict[str, Any]) -> None:
        with self._lock:
            ext = ui['ext']
            if ui.get('status') == 'running':
                return
            port = self._alloc_ui_port()
            if port is None:
                ui['status'] = 'failed'
                return
            logs = _ensure_logs_dir()
            log_file = logs / f"{ext}__ui.log"
            # Ensure UI dependencies installed (pnpm preferred)
            try:
                ui_dir = os.path.dirname(ui['start'])
                if not os.path.isdir(os.path.join(ui_dir, 'node_modules')):
                    if shutil.which('pnpm'):
                        self._popen(['pnpm', 'install', '--silent'], cwd=ui_dir, log_file=log_file)
                    else:
                        self._popen(['npm', 'install', '--silent'], cwd=ui_dir, log_file=log_file)
            except Exception:
                pass
            # Prefer executing start.sh directly; pass port as first arg
            cmd = ['bash', ui['start'], str(port)]
            env = {
                'PORT': str(port),
                'BIND_ADDRESS': '0.0.0.0',
            }
            proc = self._popen(cmd, cwd=os.path.dirname(ui['start']), log_file=log_file, env=env)
            if proc is None:
                ui['status'] = 'failed'
                return
            ui['status'] = 'running'
            ui['port'] = port
            ui['pid'] = proc.pid
            ui['process'] = proc
            ui['last_check'] = int(time.time())

    def _start_service(self, svc: Dict[str, Any]) -> None:
        with self._lock:
            key = (svc['ext'], svc['name'])
            if svc.get('status') == 'running':
                return
            port: Optional[int] = None
            # Check for fixed_port first, then dynamic port allocation
            fixed_port = svc.get('fixed_port')
            if fixed_port:
                port = int(fixed_port)
            elif bool(svc.get('requires_port')):
                port = self._alloc_svc_port()
                if port is None:
                    svc['status'] = 'failed'
                    return
            logs = _ensure_logs_dir()
            log_file = logs / f"{svc['ext']}__service_{svc['name']}.log"
            cmd = ['bash', svc['start']]
            # Only pass port as argument for dynamic port allocation
            if port is not None and bool(svc.get('requires_port')):
                cmd.append(str(port))
            # Provide common env vars
            env = {
                'PORT': str(port) if port else '',
                'AM_API_PORT': str(port) if port else '',
                'BIND_ADDRESS': '0.0.0.0',
            }
            proc = self._popen(cmd, cwd=os.path.dirname(svc['start']), log_file=log_file, env=env)
            if proc is None:
                svc['status'] = 'failed'
                return
            svc['status'] = 'running'
            svc['port'] = port
            svc['pid'] = proc.pid
            svc['process'] = proc
            svc['started_at'] = int(time.time())
            svc['last_check'] = int(time.time())
            self._services[key] = svc

    def _stop_process(self, proc: subprocess.Popen, timeout: float = 3.0) -> None:
        try:
            proc.terminate()
            try:
                proc.wait(timeout=timeout)
            except Exception:
                proc.kill()
        except Exception:
            pass

    # ---------- Public API ----------
    def start_all(self) -> None:
        """Discover and start all UIs and services.

        Intended to be called once on API startup.
        """
        print(f"[ServiceManager] Discovering extensions from: {self.extensions_root}", flush=True)
        all_exts = self._discover_extensions()
        print(f"[ServiceManager] Found {len(all_exts)} extension(s): {', '.join(all_exts) if all_exts else 'none'}", flush=True)
        
        # Filter by enabled state
        enabled_exts = [name for name in all_exts if self._is_extension_enabled(name)]
        disabled_exts = [name for name in all_exts if not self._is_extension_enabled(name)]
        
        if disabled_exts:
            print(f"[ServiceManager] Skipping {len(disabled_exts)} disabled extension(s): {', '.join(disabled_exts)}", flush=True)
        print(f"[ServiceManager] Processing {len(enabled_exts)} enabled extension(s): {', '.join(enabled_exts) if enabled_exts else 'none'}", flush=True)
        
        with self._lock:
            for name in enabled_exts:
                ui = self._discover_ui(name)
                if ui:
                    self._uis[name] = ui
                    print(f"[ServiceManager] Discovered UI for extension: {name}", flush=True)
            for name in enabled_exts:
                for svc in self._discover_services(name):
                    self._services[(svc['ext'], svc['name'])] = svc
                    print(f"[ServiceManager] Discovered service: {name}.{svc['name']}", flush=True)

        print(f"[ServiceManager] Starting {len(self._uis)} extension UI(s)...", flush=True)
        # Start UIs first
        for ui in list(self._uis.values()):
            try:
                self._start_ui(ui)
            except Exception as e:
                print(f"[ServiceManager] ERROR starting UI {ui['ext']}: {e}", flush=True)
                continue

        print(f"[ServiceManager] Starting {len(self._services)} extension service(s)...", flush=True)
        # Then services
        for svc in list(self._services.values()):
            try:
                self._start_service(svc)
            except Exception as e:
                print(f"[ServiceManager] ERROR starting service {svc['ext']}.{svc['name']}: {e}", flush=True)
                continue

        # Kick off monitor thread
        if not self._monitor_thread:
            print("[ServiceManager] Starting health monitor thread...", flush=True)
            self._monitor_thread = threading.Thread(target=self._monitor_loop, name='luna-svc-monitor', daemon=True)
            self._monitor_thread.start()
        
        print("[ServiceManager] Extension discovery and startup complete", flush=True)

    def list_extensions(self) -> List[Dict[str, Any]]:
        with self._lock:
            result: Dict[str, Dict[str, Any]] = {}
            for ext, ui in self._uis.items():
                ent = result.setdefault(ext, {'name': ext, 'ui': None, 'services': [], 'tool_count': 0, 'enabled': True})
                ent['ui'] = self._ui_snapshot(ui)
            for (ext, _svc), svc_data in self._services.items():
                ent = result.setdefault(ext, {'name': ext, 'ui': None, 'services': [], 'tool_count': 0, 'enabled': True})
                ent['services'].append(self._svc_snapshot(svc_data))
            
            # Add ALL extensions from discovery (including tool-only and disabled extensions)
            try:
                from core.utils.extension_discovery import discover_extensions
                discovered_exts = discover_extensions(self.extensions_root)
                for disc_ext in discovered_exts:
                    ext_name = disc_ext.get('name', '')
                    # Create entry if it doesn't exist (for tool-only extensions)
                    is_enabled = self._is_extension_enabled(ext_name)
                    ent = result.setdefault(ext_name, {'name': ext_name, 'ui': None, 'services': [], 'tool_count': 0, 'enabled': is_enabled})
                    # Update tool count and enabled status
                    tools = disc_ext.get('tools', [])
                    ent['tool_count'] = len(tools)
                    ent['enabled'] = is_enabled
                    
                    # Set synthetic status for extensions without running UI/services
                    if ent['ui'] is None and not ent['services']:
                        # Extension has no active UI/services
                        # Check if it has a UI folder (should have been started but wasn't)
                        has_ui_folder = disc_ext.get('has_ui', False)
                        if has_ui_folder and is_enabled:
                            # Has UI folder but not started - likely starting up or disabled
                            ent['ui'] = {
                                'status': 'offline',  # Show offline instead of "starting"
                                'port': None,
                                'pid': None,
                                'url': None,
                                'last_check': int(time.time()),
                            }
                        elif ent['tool_count'] > 0:
                            # Tool-only extension: show as "running" if enabled and has tools
                            ent['ui'] = {
                                'status': 'running' if is_enabled else 'offline',
                                'port': None,
                                'pid': None,
                                'url': None,
                                'last_check': int(time.time()),
                            }
                        elif not is_enabled:
                            # Disabled extension with no tools
                            ent['ui'] = {
                                'status': 'offline',
                                'port': None,
                                'pid': None,
                                'url': None,
                                'last_check': int(time.time()),
                            }
            except Exception as e:
                print(f"[ServiceManager] Warning: Failed to discover tools: {e}", flush=True)
            
            # Return ALL extensions (enabled and disabled) with enabled flag
            return list(result.values())

    def get_extension(self, name: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            ent: Dict[str, Any] = {'name': name, 'ui': None, 'services': [], 'tool_count': 0}
            if name in self._uis:
                ent['ui'] = self._ui_snapshot(self._uis[name])
            for (ext, svc), data in self._services.items():
                if ext == name:
                    ent['services'].append(self._svc_snapshot(data))
            if ent['ui'] is None and not ent['services']:
                return None
            
            # Add tool count
            try:
                from core.utils.extension_discovery import discover_extensions
                discovered_exts = discover_extensions(self.extensions_root)
                for disc_ext in discovered_exts:
                    if disc_ext.get('name', '') == name:
                        tools = disc_ext.get('tools', [])
                        ent['tool_count'] = len(tools)
                        break
            except Exception:
                pass
            
            return ent

    def restart_ui(self, ext_name: str) -> bool:
        with self._lock:
            ui = self._uis.get(ext_name)
            if not ui:
                return False
            proc = ui.get('process')
            if proc:
                self._stop_process(proc)
            ui['status'] = 'stopped'
            ui['pid'] = None
            ui['port'] = None
        self._start_ui(ui)  # type: ignore[arg-type]
        return True

    def restart_service(self, ext_name: str, service_name: str) -> bool:
        key = (ext_name, service_name)
        with self._lock:
            svc = self._services.get(key)
            if not svc:
                return False
            proc = svc.get('process')
            if proc:
                self._stop_process(proc)
            svc['status'] = 'stopped'
            svc['pid'] = None
            svc['started_at'] = None
            # Only clear port if not using fixed_port
            if not svc.get('fixed_port'):
                svc['port'] = None
        self._start_service(svc)  # type: ignore[arg-type]
        return True

    # ---------- Monitor ----------
    def _monitor_loop(self) -> None:
        while not self._stop_event.is_set():
            time.sleep(30)
            try:
                self._monitor_once()
            except Exception:
                continue

    def _monitor_once(self) -> None:
        with self._lock:
            # UIs: restart if process exited; health check at /healthz if port known
            for ui in self._uis.values():
                proc: Optional[subprocess.Popen] = ui.get('process')  # type: ignore[assignment]
                if proc and proc.poll() is not None:
                    ui['status'] = 'stopped'
                    ui['pid'] = None
                    ui['port'] = None
                    # restart UIs when they die
                    try:
                        self._start_ui(ui)
                    except Exception:
                        pass
                else:
                    # Process is running, check health if we have a port
                    port = ui.get('port')
                    if port and ui.get('status') in ('starting', 'running'):
                        # Try health check at /healthz
                        ok = self._http_health_check(int(port), '/healthz')
                        if ok:
                            ui['status'] = 'running'
                        # Don't change status on failure - UIs might not have /healthz endpoint
                ui['last_check'] = int(time.time())

            # Services: if requires_port and health_check, probe; restart on failure when restart_on_failure
            for key, svc in self._services.items():
                proc: Optional[subprocess.Popen] = svc.get('process')  # type: ignore[assignment]
                if proc and proc.poll() is not None:
                    svc['status'] = 'stopped'
                    svc['pid'] = None
                    svc['started_at'] = None
                    # Keep fixed port, clear dynamic port
                    if not svc.get('fixed_port'):
                        svc['port'] = None
                    cfg = svc.get('config') or {}
                    if bool(cfg.get('restart_on_failure', True)):
                        try:
                            self._start_service(svc)
                        except Exception:
                            pass
                    continue

                port = svc.get('port')
                health = (svc.get('config') or {}).get('health_check')
                # Health check if we have a port (either dynamic or fixed) and a health_check path
                if port and isinstance(health, str) and health:
                    # Grace period: don't health check for first 10 seconds after start
                    started_at = svc.get('started_at') or 0
                    time_since_start = int(time.time()) - started_at
                    if time_since_start >= 10:
                        ok = self._http_health_check(int(port), str(health))
                        if not ok and bool((svc.get('config') or {}).get('restart_on_failure', True)):
                            if proc:
                                self._stop_process(proc)
                            svc['status'] = 'stopped'
                            svc['pid'] = None
                            svc['started_at'] = None
                            # Keep fixed port, clear dynamic port
                            if not svc.get('fixed_port'):
                                svc['port'] = None
                            try:
                                self._start_service(svc)
                            except Exception:
                                pass
                svc['last_check'] = int(time.time())

    def _http_health_check(self, port: int, path: str) -> bool:
        import http.client
        try:
            conn = http.client.HTTPConnection('0.0.0.0', port, timeout=2.0)
            conn.request('GET', path)
            resp = conn.getresponse()
            ok = 200 <= resp.status < 300
            conn.close()
            return ok
        except Exception:
            return False

    # ---------- Snapshots ----------
    def _ui_snapshot(self, ui: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'status': ui.get('status'),
            'port': ui.get('port'),
            'pid': ui.get('pid'),
            'url': f"http://{os.getenv('SUPERVISOR_HOST', '127.0.0.1')}:{ui.get('port')}" if ui.get('port') else None,
            'last_check': ui.get('last_check'),
        }

    def _svc_snapshot(self, svc: Dict[str, Any]) -> Dict[str, Any]:
        cfg = svc.get('config') or {}
        return {
            'name': svc.get('name'),
            'status': svc.get('status'),
            'port': svc.get('port'),
            'pid': svc.get('pid'),
            'requires_port': bool(svc.get('requires_port')),
            'health_check': cfg.get('health_check'),
            'restart_on_failure': bool(cfg.get('restart_on_failure', True)),
            'last_check': svc.get('last_check'),
        }


# Global singleton
MANAGER: Optional[ServiceManager] = None


def get_manager() -> ServiceManager:
    global MANAGER
    if MANAGER is None:
        MANAGER = ServiceManager()
    return MANAGER


def init_and_start() -> None:
    mgr = get_manager()
    # Run discovery + startup in a thread to avoid blocking FastAPI startup
    t = threading.Thread(target=mgr.start_all, name='luna-svc-start', daemon=True)
    t.start()


