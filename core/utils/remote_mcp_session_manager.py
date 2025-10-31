#!/usr/bin/env python3
"""
Remote MCP Session Manager - Manage persistent connections to remote MCP servers
"""
import asyncio
import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from mcp import ClientSession, types
    from mcp.client.streamable_http import streamablehttp_client
except ImportError as e:
    raise ImportError(
        "mcp library required for remote MCP servers. Install with: pip install mcp"
    ) from e


# Global singleton instance for reuse across the application
_global_session_manager: Optional['RemoteMCPSessionManager'] = None
_global_session_lock = threading.Lock()


class PersistentMCPSession:
    """Manages a persistent MCP session that can be reused across tool calls."""
    
    def __init__(self, url: str, server_id: str):
        self._session = None
        self._client_context = None
        self._url = url
        self._server_id = server_id
        self._lock = threading.Lock()
        self._loop = None
        self._loop_thread = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize the persistent session in a background thread with its own event loop."""
        def run_background_loop():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            self._loop = new_loop
            
            async def setup_session():
                try:
                    self._client_context = streamablehttp_client(self._url)
                    read, write, _ = await self._client_context.__aenter__()
                    self._session = ClientSession(read, write)
                    await self._session.__aenter__()
                    await self._session.initialize()
                    self._initialized = True
                except asyncio.CancelledError:
                    # Gracefully handle cancellation during initialization
                    print(f"[RemoteMCP] Session initialization cancelled for {self._server_id}", flush=True)
                    self._initialized = False
                    self._init_error = "Initialization cancelled"
                except Exception as e:
                    print(f"[RemoteMCP] Failed to initialize session for {self._server_id}: {e}", flush=True)
                    self._initialized = False
                    self._init_error = str(e)
            
            try:
                new_loop.run_until_complete(setup_session())
                # Only run forever if initialization succeeded
                if self._initialized:
                    new_loop.run_forever()
            except asyncio.CancelledError:
                pass  # Gracefully handle cancellation
            except Exception as e:
                print(f"[RemoteMCP] Background loop error for {self._server_id}: {e}", flush=True)
            finally:
                try:
                    new_loop.close()
                except:
                    pass
        
        self._loop_thread = threading.Thread(target=run_background_loop, daemon=True)
        self._loop_thread.start()
        
        # Wait for initialization with retries
        max_wait = 10  # seconds (increased for slow connections)
        wait_step = 0.2
        waited = 0
        while waited < max_wait and not self._initialized:
            time.sleep(wait_step)
            waited += wait_step
        
        if not self._initialized:
            error_msg = getattr(self, '_init_error', 'Timeout waiting for session initialization')
            raise RuntimeError(f"Failed to initialize MCP session for {self._server_id}: {error_msg}")
    
    def call_tool_sync(self, tool_name: str, arguments: dict) -> str:
        """Call a tool synchronously using the persistent session.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool result as string (JSON or text)
        """
        if not self._loop or not self._session:
            raise RuntimeError(f"Session not initialized for {self._server_id}")
        
        async def call_async():
            try:
                result = await self._session.call_tool(tool_name, arguments=arguments)
                
                # Extract content from result
                if result.structuredContent:
                    return json.dumps(result.structuredContent, indent=2)
                elif result.content:
                    parts = []
                    for content in result.content:
                        if isinstance(content, types.TextContent):
                            parts.append(content.text)
                        else:
                            parts.append(str(content))
                    return "\n".join(parts) if parts else "<no content>"
                return "<no content>"
            except Exception as e:
                raise RuntimeError(f"Failed to call tool {tool_name} on {self._server_id}: {e}") from e
        
        future = asyncio.run_coroutine_threadsafe(call_async(), self._loop)
        try:
            return future.result(timeout=30)
        except Exception as e:
            raise RuntimeError(f"Tool call timeout or error for {tool_name} on {self._server_id}: {e}") from e
    
    async def close(self):
        """Close the persistent session."""
        if not self._loop:
            return
        
        if self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        
        time.sleep(0.2)
        
        if self._loop_thread and self._loop_thread.is_alive():
            async def cleanup():
                try:
                    if self._session:
                        await self._session.__aexit__(None, None, None)
                    if self._client_context:
                        await self._client_context.__aexit__(None, None, None)
                except Exception:
                    pass
            
            try:
                future = asyncio.run_coroutine_threadsafe(cleanup(), self._loop)
                future.result(timeout=2)
            except:
                pass
            
            if self._loop_thread:
                self._loop_thread.join(timeout=2)
        
        self._initialized = False


class RemoteMCPSessionManager:
    """Manages multiple persistent MCP sessions for remote servers."""
    
    def __init__(self, master_config: Dict[str, Any], log_dir: Optional[Path] = None):
        """Initialize session manager with master config.
        
        Args:
            master_config: Master configuration containing remote_mcp_servers
            log_dir: Optional log directory (defaults to logs/ in project root)
        """
        self._master_config = master_config
        self._sessions: Dict[str, PersistentMCPSession] = {}
        self._initialized = False
        self._session_health: Dict[str, Dict[str, Any]] = {}
        
        # Setup log directory
        if log_dir is None:
            # Find project root (3 levels up from this file)
            project_root = Path(__file__).resolve().parents[2]
            log_dir = project_root / 'logs'
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._log_file = self._log_dir / 'remote_mcp_sessions.log'
    
    def _log(self, message: str):
        """Write a log message to the log file."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] {message}\n"
        try:
            with open(self._log_file, 'a') as f:
                f.write(log_line)
        except Exception as e:
            print(f"[RemoteMCP] Failed to write log: {e}", flush=True)
    
    def _write_tools_manifest(self):
        """Write comprehensive tools manifest to log."""
        manifest = {
            "timestamp": datetime.now().isoformat(),
            "servers": {},
            "summary": {
                "total_servers": len(self._sessions),
                "total_tools": 0,
                "enabled_tools": 0
            }
        }
        
        for server_id, server_config in self._master_config.get('remote_mcp_servers', {}).items():
            if server_id not in self._sessions:
                continue
            
            tools_data = []
            for tool_name, tool_config in server_config.get('tools', {}).items():
                tools_data.append({
                    "name": tool_name,
                    "enabled": tool_config.get('enabled', True),
                    "docstring": tool_config.get('docstring', '')[:200],  # Truncate long descriptions
                    "has_schema": bool(tool_config.get('input_schema'))
                })
                manifest["summary"]["total_tools"] += 1
                if tool_config.get('enabled', True):
                    manifest["summary"]["enabled_tools"] += 1
            
            manifest["servers"][server_id] = {
                "enabled": server_config.get('enabled', True),
                "tool_count": server_config.get('tool_count', 0),
                "health": self._session_health.get(server_id, {"status": "unknown"}),
                "tools": tools_data
            }
        
        # Write manifest to separate JSON file
        manifest_file = self._log_dir / 'remote_mcp_tools_manifest.json'
        try:
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)
            self._log(f"Tools manifest written to {manifest_file}")
        except Exception as e:
            self._log(f"Failed to write tools manifest: {e}")
    
    async def initialize_all(self):
        """Initialize all enabled remote MCP server sessions."""
        self._log("="*60)
        self._log("REMOTE MCP SESSION INITIALIZATION")
        self._log("="*60)
        
        remote_servers = self._master_config.get('remote_mcp_servers', {})
        
        if not remote_servers:
            print("[RemoteMCP] No remote MCP servers configured", flush=True)
            self._log("No remote MCP servers configured")
            self._initialized = True
            return
        
        print(f"[RemoteMCP] Initializing {len(remote_servers)} remote MCP server(s)...", flush=True)
        self._log(f"Initializing {len(remote_servers)} remote MCP server(s)")
        
        for server_id, server_config in remote_servers.items():
            # Skip disabled servers
            if not server_config.get('enabled', True):
                print(f"[RemoteMCP] Skipping disabled server: {server_id}", flush=True)
                self._log(f"Skipping disabled server: {server_id}")
                self._session_health[server_id] = {
                    "status": "disabled",
                    "timestamp": datetime.now().isoformat()
                }
                continue
            
            url = server_config.get('url')
            if not url:
                print(f"[RemoteMCP] Warning: Server {server_id} has no URL, skipping", flush=True)
                self._log(f"Warning: Server {server_id} has no URL")
                self._session_health[server_id] = {
                    "status": "error",
                    "error": "No URL configured",
                    "timestamp": datetime.now().isoformat()
                }
                continue
            
            try:
                print(f"[RemoteMCP] Connecting to {server_id}...", flush=True)
                self._log(f"Connecting to {server_id} ({url[:50]}...)")
                
                session = PersistentMCPSession(url, server_id)
                await session.initialize()
                self._sessions[server_id] = session
                
                tool_count = server_config.get('tool_count', 0)
                enabled_tools = sum(1 for t in server_config.get('tools', {}).values() if t.get('enabled', True))
                
                print(f"[RemoteMCP] ✓ Connected to {server_id} ({tool_count} tools)", flush=True)
                self._log(f"✓ Connected to {server_id}")
                self._log(f"  Tools: {tool_count} total, {enabled_tools} enabled")
                
                # Log individual tools
                for tool_name, tool_config in server_config.get('tools', {}).items():
                    status = "enabled" if tool_config.get('enabled', True) else "disabled"
                    self._log(f"    - {tool_name}: {status}")
                
                self._session_health[server_id] = {
                    "status": "connected",
                    "tool_count": tool_count,
                    "enabled_tools": enabled_tools,
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                error_msg = str(e)
                print(f"[RemoteMCP] ✗ Failed to connect to {server_id}: {e}", flush=True)
                self._log(f"✗ Failed to connect to {server_id}: {error_msg}")
                self._session_health[server_id] = {
                    "status": "error",
                    "error": error_msg,
                    "timestamp": datetime.now().isoformat()
                }
                # Continue with other servers even if one fails
                continue
        
        self._initialized = True
        success_count = len(self._sessions)
        print(f"[RemoteMCP] Initialized {success_count} remote MCP session(s)", flush=True)
        self._log(f"Initialization complete: {success_count}/{len(remote_servers)} servers connected")
        self._log("="*60)
        
        # Write comprehensive tools manifest
        self._write_tools_manifest()
    
    def call_tool(self, server_id: str, tool_name: str, arguments: dict) -> str:
        """Call a tool on a remote MCP server.
        
        Args:
            server_id: Server identifier
            tool_name: Tool name
            arguments: Tool arguments
            
        Returns:
            Tool result as string
        """
        if server_id not in self._sessions:
            raise ValueError(f"No active session for server: {server_id}")
        
        session = self._sessions[server_id]
        return session.call_tool_sync(tool_name, arguments)
    
    def get_active_servers(self) -> list:
        """Get list of active server IDs.
        
        Returns:
            List of server IDs with active sessions
        """
        return list(self._sessions.keys())
    
    def has_session(self, server_id: str) -> bool:
        """Check if a session exists for a server.
        
        Args:
            server_id: Server identifier
            
        Returns:
            True if session exists and is active
        """
        return server_id in self._sessions
    
    async def close_all(self):
        """Close all sessions."""
        print("[RemoteMCP] Closing all sessions...", flush=True)
        for server_id, session in self._sessions.items():
            try:
                await session.close()
                print(f"[RemoteMCP] Closed session for {server_id}", flush=True)
            except Exception as e:
                print(f"[RemoteMCP] Error closing session for {server_id}: {e}", flush=True)
        
        self._sessions.clear()
        self._initialized = False
        print("[RemoteMCP] All sessions closed", flush=True)


# ============================================================================
# Global Session Manager Functions
# ============================================================================

def get_global_session_manager() -> Optional['RemoteMCPSessionManager']:
    """Get or create the global session manager singleton.
    
    This function initializes the session manager once on first call and
    reuses it for all subsequent calls, making it efficient for tools that
    need remote MCP access.
    
    Returns:
        Global RemoteMCPSessionManager instance, or None if no remote servers configured
    """
    global _global_session_manager
    
    with _global_session_lock:
        if _global_session_manager is None:
            # Try to initialize from master_config
            try:
                # Calculate project root from this file's location
                project_root = Path(__file__).resolve().parents[2]
                master_config_path = project_root / 'core' / 'master_config.json'
                
                if not master_config_path.exists():
                    print(f"[RemoteMCP] No master_config.json found, skipping global session manager", flush=True)
                    return None
                
                with open(master_config_path, 'r') as f:
                    master_config = json.load(f)
                
                remote_servers = master_config.get('remote_mcp_servers', {})
                if not remote_servers:
                    print(f"[RemoteMCP] No remote MCP servers configured", flush=True)
                    return None
                
                print(f"[RemoteMCP] Initializing global session manager with {len(remote_servers)} remote server(s)...", flush=True)
                _global_session_manager = RemoteMCPSessionManager(master_config)
                
                # Initialize - check if we're in an async context
                try:
                    # Try to get the running loop
                    loop = asyncio.get_running_loop()
                    # We're in an async context - schedule initialization in background
                    print(f"[RemoteMCP] Detected async context, initializing in background thread...", flush=True)
                    
                    # Run initialization in a separate thread with its own loop
                    import concurrent.futures
                    def init_in_thread():
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            new_loop.run_until_complete(_global_session_manager.initialize_all())
                            return True
                        except Exception as e:
                            print(f"[RemoteMCP] Thread initialization error: {e}", flush=True)
                            return False
                        finally:
                            new_loop.close()
                    
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(init_in_thread)
                        success = future.result(timeout=30)
                        if success:
                            print(f"[RemoteMCP] ✓ Global session manager initialized successfully", flush=True)
                        else:
                            raise RuntimeError("Failed to initialize in background thread")
                            
                except RuntimeError:
                    # No running loop - we're in sync context
                    print(f"[RemoteMCP] Sync context, initializing directly...", flush=True)
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(_global_session_manager.initialize_all())
                        print(f"[RemoteMCP] ✓ Global session manager initialized successfully", flush=True)
                    finally:
                        loop.close()
                    
            except Exception as e:
                print(f"[RemoteMCP] ✗ Failed to initialize global session manager: {e}", flush=True)
                import traceback
                traceback.print_exc()
                _global_session_manager = None
                return None
        
        return _global_session_manager


def reset_global_session_manager():
    """Reset the global session manager.
    
    Useful when configuration changes or during system restarts.
    The next call to get_global_session_manager() will reinitialize.
    """
    global _global_session_manager
    with _global_session_lock:
        if _global_session_manager is not None:
            print(f"[RemoteMCP] Resetting global session manager", flush=True)
        _global_session_manager = None

