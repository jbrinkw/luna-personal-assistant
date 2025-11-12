"""
External Services Manager
Handles discovery, installation, management, and monitoring of external services
"""
import json
import subprocess
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from .external_service_schemas import (
    ServiceDefinition,
    ConfigForm,
)
from .caddy_control import reload_caddy


class ExternalServicesManager:
    """Manages external services (databases, infrastructure programs, etc.)"""
    
    def __init__(self, repo_path: Path):
        """
        Initialize the external services manager
        
        Args:
            repo_path: Root path of the Luna repository
        """
        self.repo_path = Path(repo_path)
        self.services_dir = self.repo_path / "external_services"
        self.luna_dir = self.repo_path / ".luna"
        self.logs_dir = self.luna_dir / "logs"
        self.registry_path = self.luna_dir / "external_services.json"
        self.ui_routes_path = self.luna_dir / "external_service_routes.json"
        
        # Ensure directories exist
        self.services_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def bootstrap_bundled_services(self) -> None:
        """
        [DISABLED] Bootstrap bundled external service definitions from the repo root.
        
        This method is no longer called during startup. Bundled *-docker.json files
        in the repo root are kept as examples/reference only. Services should be 
        installed via the Hub UI or API upload endpoint.
        """
        print("[ExternalServicesManager] bootstrap_bundled_services() is disabled - use Hub UI to install services")
        return
        
        # Legacy code kept for reference:
        try:
            # Look for bundled service definitions in repo root
            bundled_files = list(self.repo_path.glob("*-docker.json"))
            
            if not bundled_files:
                print("[ExternalServicesManager] No bundled service definitions found")
                return
            
            print(f"[ExternalServicesManager] Found {len(bundled_files)} bundled service definition(s)")
            
            for bundled_file in bundled_files:
                try:
                    # Load and validate the service definition
                    with open(bundled_file, 'r') as f:
                        service_data = json.load(f)
                    
                    # Validate with Pydantic
                    service_def = ServiceDefinition(**service_data)
                    service_name = service_def.name
                    
                    # Check if service directory already exists
                    service_dir = self.services_dir / service_name
                    service_json = service_dir / "service.json"
                    
                    if service_json.exists():
                        print(f"[ExternalServicesManager] Service {service_name} already exists, skipping")
                        continue
                    
                    # Create service directory and copy definition
                    service_dir.mkdir(parents=True, exist_ok=True)
                    
                    with open(service_json, 'w') as f:
                        json.dump(service_data, f, indent=2)
                    
                    print(f"[ExternalServicesManager] Bootstrapped service: {service_name} from {bundled_file.name}")
                    
                except Exception as e:
                    print(f"[ExternalServicesManager] Error bootstrapping {bundled_file.name}: {e}")
                    continue
            
        except Exception as e:
            print(f"[ExternalServicesManager] Error during bootstrap: {e}")

    def get_ui_routes(self) -> Dict[str, Dict[str, Any]]:
        """
        Read persisted UI routing metadata.

        Returns:
            Mapping of service name to UI metadata dictionaries.
        """
        if not self.ui_routes_path.exists():
            return {}

        try:
            with open(self.ui_routes_path, "r") as f:
                return json.load(f)
        except Exception as exc:
            print(f"[ExternalServicesManager] Error reading UI routes: {exc}")
            return {}

    def save_ui_routes(self, routes: Dict[str, Dict[str, Any]]) -> None:
        """Persist UI routing metadata to disk."""
        try:
            with open(self.ui_routes_path, "w") as f:
                json.dump(routes, f, indent=2)
        except Exception as exc:
            print(f"[ExternalServicesManager] Error saving UI routes: {exc}")

    def _normalize_slug(self, value: str) -> str:
        """Convert arbitrary strings to a URL-safe slug."""
        slug = value.strip().lower().replace(" ", "-")
        slug = re.sub(r"[^a-z0-9\-]+", "-", slug)
        slug = re.sub(r"-{2,}", "-", slug).strip("-")
        return slug or "service"

    def _assign_unique_slug(self, base_slug: str, service_name: str, routes: Dict[str, Dict[str, Any]]) -> str:
        """Ensure slug uniqueness across all services."""
        existing = {meta.get("slug"): name for name, meta in routes.items() if meta.get("slug")}
        if existing.get(base_slug) in (None, service_name):
            return base_slug

        suffix = 2
        while True:
            candidate = f"{base_slug}-{suffix}"
            owner = existing.get(candidate)
            if owner is None or owner == service_name:
                return candidate
            suffix += 1

    def _compute_ui_metadata(
        self,
        service_name: str,
        service_def: ServiceDefinition,
        config: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Derive UI routing metadata from the service definition and config."""
        if not service_def.ui:
            return None

        ui_cfg = service_def.ui
        try:
            port = ui_cfg.port
            if port is None:
                # Pull from config and coerce to integer
                raw_value = config.get(ui_cfg.port_field, None)
                if raw_value is None:
                    print(
                        f"[ExternalServicesManager] UI port_field '{ui_cfg.port_field}' missing in config for {service_name}"
                    )
                    return None
                port = int(raw_value)

            if port <= 0 or port > 65535:
                raise ValueError("port out of range")
        except Exception as exc:  # noqa: BLE001
            print(f"[ExternalServicesManager] Invalid UI port for {service_name}: {exc}")
            return None

        base_path = ui_cfg.base_path.strip("/ ")
        base_path = base_path or "ext_service"
        raw_slug = ui_cfg.slug or service_name

        metadata: Dict[str, Any] = {
            "service": service_name,
            "base_path": base_path,
            "slug": raw_slug,
            "port": port,
            "scheme": ui_cfg.scheme,
            "strip_prefix": ui_cfg.strip_prefix,
            "enforce_trailing_slash": ui_cfg.enforce_trailing_slash,
            "open_mode": ui_cfg.open_mode,
        }
        return metadata

    def _set_registry_ui_metadata(self, service_name: str, metadata: Optional[Dict[str, Any]]) -> None:
        """Persist derived UI metadata inside the registry entry."""
        registry = self.get_registry()
        if service_name not in registry:
            return

        entry = registry[service_name]
        if metadata is None:
            entry.pop("ui", None)
        else:
            entry["ui"] = {
                "path": metadata.get("path"),
                "path_with_slash": metadata.get("path_with_slash"),
                "slug": metadata.get("slug"),
                "base_path": metadata.get("base_path"),
                "open_mode": metadata.get("open_mode"),
                "scheme": metadata.get("scheme"),
            }

        registry[service_name] = entry
        self.save_registry(registry)

    def _sync_ui_route(
        self,
        service_name: str,
        service_def: ServiceDefinition,
        config: Dict[str, Any],
    ) -> None:
        """Compute and persist UI routing metadata, then reload Caddy if changed."""
        routes = self.get_ui_routes()
        metadata = self._compute_ui_metadata(service_name, service_def, config)

        if metadata is None:
            if service_name in routes:
                routes.pop(service_name, None)
                self.save_ui_routes(routes)
                self._set_registry_ui_metadata(service_name, None)
                self._reload_caddy(f"ui-remove:{service_name}")
            return

        # Normalise slug and ensure uniqueness
        base_slug = self._normalize_slug(metadata["slug"])
        metadata["slug"] = self._assign_unique_slug(base_slug, service_name, routes)

        path = f"/{metadata['base_path'].strip('/')}/{metadata['slug']}".replace("//", "/")
        metadata["path"] = path
        path_with_slash = f"{path.rstrip('/')}/" if metadata["enforce_trailing_slash"] else path
        metadata["path_with_slash"] = path_with_slash
        previous = routes.get(service_name)
        previous_comparable = dict(previous) if previous else None
        if previous_comparable:
            previous_comparable.pop("last_updated", None)

        current_comparable = dict(metadata)
        current_comparable.pop("last_updated", None)

        metadata["last_updated"] = datetime.now().isoformat()

        if previous_comparable == current_comparable:
            # Preserve existing last_updated to avoid unnecessary churn.
            metadata["last_updated"] = previous.get("last_updated") if previous else metadata["last_updated"]
            routes[service_name] = {**previous, **metadata} if previous else metadata
            self.save_ui_routes(routes)
            self._set_registry_ui_metadata(service_name, routes[service_name])
            return

        routes[service_name] = metadata
        self.save_ui_routes(routes)
        self._set_registry_ui_metadata(service_name, metadata)
        self._reload_caddy(f"ui-sync:{service_name}")

    def _env_file_path(self) -> Path:
        """Return the path to the repository .env file."""
        return self.repo_path / ".env"

    def _format_env_value(self, value: Any) -> str:
        """
        Format a value for writing into .env.
        Quotes values containing whitespace or shell-sensitive characters.
        """
        text = "" if value is None else str(value)
        if not text:
            return ""

        if re.search(r"\s|#|=|\"|'", text):
            escaped = text.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
        return text

    def _render_template(self, template: str, context: Dict[str, Any]) -> str:
        """Render a lightweight {{ placeholder }} template using the provided context."""
        pattern = re.compile(r"{{\s*([^}]+)\s*}}")

        def substitute(match: re.Match) -> str:
            key = match.group(1).strip()
            return str(context.get(key, ""))

        return pattern.sub(substitute, template)

    def _build_env_assignments(
        self,
        service_name: str,
        service_def: ServiceDefinition,
        config: Dict[str, Any],
    ) -> Dict[str, str]:
        """
        Compute environment variable assignments for a service installation.

        Prefers explicit post_install_env templates. Falls back to matching
        config keys when templates are absent.
        """
        if not service_def.provides_vars:
            return {}

        # Build context with multiple casings for convenience.
        context: Dict[str, Any] = {
            "service_name": service_name,
            "service_dir": str(self.services_dir / service_name),
            "repo_root": str(self.repo_path),
        }
        for key, value in config.items():
            context[key] = value
            if isinstance(key, str):
                context[key.lower()] = value
                context[key.upper()] = value

        resolved: Dict[str, str] = {}
        templates = service_def.post_install_env or {}

        if templates:
            for env_key, template in templates.items():
                if env_key not in service_def.provides_vars:
                    continue
                try:
                    rendered = self._render_template(template, context)
                except Exception as exc:  # noqa: BLE001
                    print(
                        f"[ExternalServicesManager] Failed to render env template for {service_name}:{env_key}: {exc}"
                    )
                    continue
                resolved[env_key] = rendered
        else:
            for env_key in service_def.provides_vars:
                lookup = env_key.lower()
                if lookup in context:
                    resolved[env_key] = "" if context[lookup] is None else str(context[lookup])

        return resolved

    def _write_env_assignments(self, assignments: Dict[str, str]) -> None:
        """Write or update environment variables in the repository .env file."""
        if not assignments:
            return

        env_path = self._env_file_path()
        lines: List[str] = []
        if env_path.exists():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    lines = f.read().splitlines()
            except Exception as exc:  # noqa: BLE001
                print(f"[ExternalServicesManager] Warning: Failed to read .env file: {exc}")
                lines = []

        used_keys: set[str] = set()
        updated_lines: List[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                updated_lines.append(line)
                continue

            key, sep, _ = line.partition("=")
            if not sep:
                updated_lines.append(line)
                continue

            key = key.strip()
            if key in assignments:
                used_keys.add(key)
                updated_lines.append(line)
            else:
                updated_lines.append(line)

        for key, value in assignments.items():
            if key not in used_keys:
                formatted_value = self._format_env_value(value)
                updated_lines.append(f"{key}={formatted_value}")

        try:
            with open(env_path, "w", encoding="utf-8") as f:
                f.write("\n".join(updated_lines).rstrip() + "\n")
        except Exception as exc:  # noqa: BLE001
            print(f"[ExternalServicesManager] Warning: Failed to update .env file: {exc}")

    def _remove_env_vars(self, keys: List[str]) -> None:
        """Remove specified keys from the repository .env file."""
        if not keys:
            return

        env_path = self._env_file_path()
        if not env_path.exists():
            return

        try:
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except Exception as exc:  # noqa: BLE001
            print(f"[ExternalServicesManager] Warning: Failed to read .env for removal: {exc}")
            return

        keys_set = set(keys)
        updated_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                updated_lines.append(line)
                continue

            key, sep, _ = line.partition("=")
            if not sep:
                updated_lines.append(line)
                continue

            if key.strip() in keys_set:
                continue

            updated_lines.append(line)

        try:
            with open(env_path, "w", encoding="utf-8") as f:
                if updated_lines:
                    f.write("\n".join(updated_lines).rstrip() + "\n")
                else:
                    f.write("")
        except Exception as exc:  # noqa: BLE001
            print(f"[ExternalServicesManager] Warning: Failed to write .env after removal: {exc}")

    def _remove_ui_route(self, service_name: str) -> None:
        """Remove any persisted UI routing metadata for a service."""
        routes = self.get_ui_routes()
        if service_name in routes:
            routes.pop(service_name, None)
            self.save_ui_routes(routes)
            self._set_registry_ui_metadata(service_name, None)
            self._reload_caddy(f"ui-delete:{service_name}")
    
    def _reload_caddy(self, reason: str) -> None:
        """Best-effort Caddy reload for external service lifecycle events."""
        try:
            reload_caddy(self.repo_path, reason=f"external-services:{reason}", quiet=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[ExternalServicesManager] Warning: Failed to reload Caddy ({reason}): {exc}")
    
    def discover_available_services(self) -> List[Dict[str, Any]]:
        """
        Scan external_services/ directory for service.json files
        
        Returns:
            List of service definitions with metadata
        """
        services = []
        
        if not self.services_dir.exists():
            return services
        
        for service_dir in self.services_dir.iterdir():
            if not service_dir.is_dir():
                continue
            
            service_json_path = service_dir / "service.json"
            if not service_json_path.exists():
                continue
            
            try:
                with open(service_json_path, 'r') as f:
                    service_data = json.load(f)
                
                # Validate with Pydantic
                service_def = ServiceDefinition(**service_data)
                
                # Check if installed
                registry = self.get_registry()
                is_installed = service_def.name in registry
                
                services.append({
                    **service_def.dict(),
                    "installed": is_installed
                })
            except Exception as e:
                print(f"[ExternalServicesManager] Error loading service from {service_dir}: {e}")
                continue
        
        return services
    
    def get_service_definition(self, service_name: str) -> Optional[ServiceDefinition]:
        """
        Get service definition by name
        
        Args:
            service_name: Name of the service
            
        Returns:
            ServiceDefinition or None if not found
        """
        service_dir = self.services_dir / service_name
        service_json_path = service_dir / "service.json"
        
        if not service_json_path.exists():
            return None
        
        try:
            with open(service_json_path, 'r') as f:
                service_data = json.load(f)
            return ServiceDefinition(**service_data)
        except Exception as e:
            print(f"[ExternalServicesManager] Error loading service definition for {service_name}: {e}")
            return None
    
    def get_config_form(self, service_name: str) -> Optional[ConfigForm]:
        """
        Get configuration form for a service
        
        Args:
            service_name: Name of the service
            
        Returns:
            ConfigForm or None if not found
        """
        # First check if service definition has inline config_form
        service_def = self.get_service_definition(service_name)
        if service_def and service_def.config_form:
            return service_def.config_form
        
        # Fall back to separate config-form.json file
        service_dir = self.services_dir / service_name
        config_form_path = service_dir / "config-form.json"
        
        if not config_form_path.exists():
            return ConfigForm(fields=[])  # Empty form if not defined
        
        try:
            with open(config_form_path, 'r') as f:
                form_data = json.load(f)
            return ConfigForm(**form_data)
        except Exception as e:
            print(f"[ExternalServicesManager] Error loading config form for {service_name}: {e}")
            return ConfigForm(fields=[])
    
    def get_registry(self) -> Dict[str, Dict[str, Any]]:
        """
        Read or create the external services registry
        
        Returns:
            Dictionary of installed services and their metadata
        """
        if not self.registry_path.exists():
            return {}
        
        try:
            with open(self.registry_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ExternalServicesManager] Error reading registry: {e}")
            return {}
    
    def save_registry(self, registry: Dict[str, Dict[str, Any]]):
        """
        Save the external services registry
        
        Args:
            registry: Dictionary of services to save
        """
        try:
            with open(self.registry_path, 'w') as f:
                json.dump(registry, f, indent=2)
        except Exception as e:
            print(f"[ExternalServicesManager] Error saving registry: {e}")
    
    def update_registry(self, service_name: str, data: Dict[str, Any]):
        """
        Update a single service entry in the registry
        
        Args:
            service_name: Name of the service
            data: Dictionary of fields to update
        """
        registry = self.get_registry()
        
        if service_name not in registry:
            registry[service_name] = {}
        
        registry[service_name].update(data)
        self.save_registry(registry)
    
    def remove_from_registry(self, service_name: str):
        """
        Remove a service from the registry
        
        Args:
            service_name: Name of the service to remove
        """
        registry = self.get_registry()
        
        if service_name in registry:
            del registry[service_name]
            self.save_registry(registry)
    
    def get_service_config(self, service_name: str) -> Optional[Dict[str, Any]]:
        """
        Read saved user configuration for a service
        
        Args:
            service_name: Name of the service
            
        Returns:
            Configuration dictionary or None if not found
        """
        config_path = self.services_dir / service_name / "config.json"
        
        if not config_path.exists():
            return None
        
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ExternalServicesManager] Error reading config for {service_name}: {e}")
            return None
    
    def save_service_config(self, service_name: str, config: Dict[str, Any]):
        """
        Save user configuration for a service
        
        Args:
            service_name: Name of the service
            config: Configuration dictionary to save
        """
        service_dir = self.services_dir / service_name
        service_dir.mkdir(parents=True, exist_ok=True)
        
        config_path = service_dir / "config.json"
        
        # Add installation timestamp if not present
        if "installed_at" not in config:
            config["installed_at"] = datetime.now().isoformat()
        
        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"[ExternalServicesManager] Error saving config for {service_name}: {e}")
            return

        # Update UI routing metadata whenever configuration changes.
        service_def = self.get_service_definition(service_name)
        if service_def:
            self._sync_ui_route(service_name, service_def, config)
    
    def get_log_path(self, service_name: str) -> Path:
        """
        Get the log file path for a service
        
        Args:
            service_name: Name of the service
            
        Returns:
            Path to the log file
        """
        return self.logs_dir / f"{service_name}.log"
    
    def ensure_log_directory(self):
        """Create logs directory if it doesn't exist"""
        self.logs_dir.mkdir(parents=True, exist_ok=True)
    
    def _write_to_log(self, service_name: str, content: str) -> None:
        """
        Append content to a service's log file
        
        Args:
            service_name: Name of the service
            content: Content to write
        """
        try:
            log_path = self.get_log_path(service_name)
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            print(f"[ExternalServicesManager] Warning: Failed to write to log for {service_name}: {e}")
    
    def capture_docker_logs(self, service_name: str, container_name: str, lines: int = 100) -> None:
        """
        Capture recent Docker container logs and append to service log file
        
        Args:
            service_name: Name of the service
            container_name: Name of the Docker container
            lines: Number of recent log lines to capture
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Try to get docker logs
            result = subprocess.run(
                ["docker", "logs", "--tail", str(lines), container_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                docker_logs = result.stdout + result.stderr
                if docker_logs.strip():
                    self._write_to_log(service_name, f"\n[{timestamp}] Docker container logs ({container_name}):\n")
                    self._write_to_log(service_name, docker_logs)
                    self._write_to_log(service_name, "\n" + "=" * 80 + "\n")
                else:
                    self._write_to_log(service_name, f"\n[{timestamp}] Docker container logs ({container_name}): (empty)\n")
            else:
                self._write_to_log(service_name, f"\n[{timestamp}] Failed to capture Docker logs for {container_name}: {result.stderr}\n")
                
        except Exception as e:
            print(f"[ExternalServicesManager] Warning: Failed to capture Docker logs for {service_name}: {e}")
    
    def tail_log(self, service_name: str, lines: int = 100) -> str:
        """
        Read last N lines from a service log file
        
        Args:
            service_name: Name of the service
            lines: Number of lines to read from end
            
        Returns:
            Log content as string
        """
        log_path = self.get_log_path(service_name)
        
        if not log_path.exists():
            return ""
        
        try:
            # Use tail command for efficiency with large files
            result = subprocess.run(
                ["tail", "-n", str(lines), str(log_path)],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout
        except Exception as e:
            print(f"[ExternalServicesManager] Error reading log for {service_name}: {e}")
            # Fallback to Python reading
            try:
                with open(log_path, 'r') as f:
                    all_lines = f.readlines()
                    return ''.join(all_lines[-lines:])
            except Exception as e2:
                print(f"[ExternalServicesManager] Fallback log read failed: {e2}")
                return ""
    
    def get_command(self, service_def: ServiceDefinition, action: str) -> Optional[str]:
        """
        Get command for a specific action from service definition
        Supports both new commands object and legacy command fields
        
        Args:
            service_def: Service definition
            action: Action name (install, start, stop, restart, health_check, enable_startup, disable_startup, uninstall)
            
        Returns:
            Command string or None if not found
        """
        # Check if service has new commands object
        if service_def.commands:
            command_map = {
                "install": service_def.commands.install,
                "uninstall": service_def.commands.uninstall,
                "start": service_def.commands.start,
                "stop": service_def.commands.stop,
                "restart": service_def.commands.restart,
                "health_check": service_def.commands.health_check,
                "enable_startup": service_def.commands.enable_startup,
                "disable_startup": service_def.commands.disable_startup,
            }
            return command_map.get(action)
        
        # Fall back to legacy command fields
        legacy_map = {
            "install": service_def.install_cmd,
            "uninstall": service_def.uninstall_cmd,
            "start": service_def.start_cmd,
            "stop": service_def.stop_cmd,
            "restart": service_def.restart_cmd,
            "health_check": service_def.health_check_cmd,
            "enable_startup": service_def.enable_startup_cmd,
            "disable_startup": service_def.disable_startup_cmd,
        }
        return legacy_map.get(action)
    
    def interpolate_command(self, command: str, service_name: str, service_def: ServiceDefinition) -> str:
        """
        Replace placeholders in commands with actual values
        Supports both legacy {placeholder} and new {{variable}} template syntax
        
        Args:
            command: Command string with placeholders
            service_name: Name of the service
            service_def: Service definition
            
        Returns:
            Interpolated command string
        
        Raises:
            ValueError: If required variables are missing from config
        """
        config_path = self.services_dir / service_name / "config.json"
        working_dir = service_def.working_dir or str(self.repo_path)
        service_dir = self.services_dir / service_name
        data_dir = service_dir / "data"
        
        # Get user configuration
        config = self.get_service_config(service_name) or {}

        # Build extended config with auto-assigned system variables
        extended_config = dict(config)

        # Load master_config to get deployment settings
        master_config_path = self.repo_path / "core" / "master_config.json"
        public_domain = ""
        deployment_mode = ""
        if master_config_path.exists():
            try:
                with open(master_config_path, 'r') as f:
                    master_config = json.load(f)
                    public_domain = master_config.get("public_domain", "")
                    deployment_mode = master_config.get("deployment_mode", "")
            except Exception as e:
                print(f"[ExternalServicesManager] Warning: Could not load master_config for template vars: {e}")

        # Auto-assign common system variables (case variations for convenience)
        auto_vars = {
            'service_name': service_name,
            'SERVICE_NAME': service_name,
            'container_name': f"luna-{service_name}",
            'CONTAINER_NAME': f"luna-{service_name}",
            'service_dir': str(service_dir),
            'SERVICE_DIR': str(service_dir),
            'data_dir': str(data_dir),
            'DATA_DIR': str(data_dir),
            'repo_root': str(self.repo_path),
            'REPO_ROOT': str(self.repo_path),
            'public_domain': public_domain,
            'PUBLIC_DOMAIN': public_domain,
            'deployment_mode': deployment_mode,
            'DEPLOYMENT_MODE': deployment_mode,
        }
        
        # Add auto-vars only if not already in user config (user config takes precedence)
        for key, value in auto_vars.items():
            if key not in extended_config:
                extended_config[key] = value
        
        # Start with command
        result = command
        
        # First, replace {{variable}} template syntax with config values
        # Find all {{variable}} patterns (with optional whitespace)
        template_pattern = r'\{\{\s*(\w+)\s*\}\}'
        matches = re.findall(template_pattern, result)
        
        # Build case-insensitive lookup for extended config
        config_lower = {k.lower(): (k, v) for k, v in extended_config.items()}
        
        missing_vars = []
        for var_name in matches:
            # Try exact match first
            if var_name in extended_config:
                value = str(extended_config[var_name])
                # Replace all variations: {{var}}, {{ var }}, {{  var  }}, etc.
                result = re.sub(r'\{\{\s*' + re.escape(var_name) + r'\s*\}\}', value, result)
            # Try case-insensitive match
            elif var_name.lower() in config_lower:
                original_key, value = config_lower[var_name.lower()]
                # Replace all variations with case-insensitive pattern
                result = re.sub(r'\{\{\s*' + re.escape(var_name) + r'\s*\}\}', str(value), result, flags=re.IGNORECASE)
            else:
                missing_vars.append(var_name)
        
        # If there are missing variables, raise an error
        if missing_vars:
            error_msg = f"Missing required configuration for {service_name}: {', '.join(missing_vars)}"
            print(f"[ExternalServicesManager] ERROR: {error_msg}")
            print(f"[ExternalServicesManager] Available config: {', '.join(config.keys()) if config else 'none'}")
            print(f"[ExternalServicesManager] Auto-assigned: {', '.join(auto_vars.keys())}")
            print(f"[ExternalServicesManager] Command: {command}")
            # Remove any remaining template variables to prevent syntax errors
            for var_name in missing_vars:
                result = re.sub(r'\{\{\s*' + re.escape(var_name) + r'\s*\}\}', '', result)
            raise ValueError(error_msg)
        
        # Then replace legacy {placeholder} syntax
        port = config.get("port", "")
        replacements = {
            "{config_file}": str(config_path),
            "{working_dir}": working_dir,
            "{port}": str(port)
        }
        
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, value)
        
        return result
    
    def execute_command(
        self,
        command: str,
        timeout: int = 30,
        working_dir: Optional[str] = None,
        service_name: Optional[str] = None
    ) -> Tuple[bool, str, int]:
        """
        Execute a shell command with timeout and error handling
        
        Args:
            command: Command to execute
            timeout: Timeout in seconds
            working_dir: Working directory (defaults to repo root)
            service_name: Name of service (for logging)
            
        Returns:
            Tuple of (success, output, exit_code)
        """
        if working_dir is None:
            working_dir = str(self.repo_path)
        
        # Prepare log entry header
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_header = f"[{timestamp}] Executing command for service '{service_name or 'unknown'}':\n{command}\n"
        log_separator = "=" * 80 + "\n"
        
        # Load .env variables into environment
        env = os.environ.copy()
        env_file = self.repo_path / ".env"
        if env_file.exists():
            try:
                with open(env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            env[key] = value
            except Exception as e:
                print(f"[ExternalServicesManager] Warning: Failed to load .env: {e}")
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env
            )
            
            output = result.stdout + result.stderr
            success = result.returncode == 0
            
            # Write to log file if service_name is provided
            if service_name:
                self._write_to_log(service_name, log_header)
                self._write_to_log(service_name, f"Exit Code: {result.returncode}\n")
                if output:
                    self._write_to_log(service_name, f"Output:\n{output}\n")
                else:
                    self._write_to_log(service_name, "Output: (empty)\n")
                self._write_to_log(service_name, log_separator)
            
            return success, output, result.returncode
            
        except subprocess.TimeoutExpired:
            error_msg = f"Command timed out after {timeout} seconds"
            print(f"[ExternalServicesManager] {error_msg}: {command}")
            
            # Log timeout
            if service_name:
                self._write_to_log(service_name, log_header)
                self._write_to_log(service_name, f"ERROR: {error_msg}\n")
                self._write_to_log(service_name, log_separator)
            
            return False, error_msg, -1
            
        except FileNotFoundError:
            error_msg = f"Command executable not found"
            print(f"[ExternalServicesManager] {error_msg}: {command}")
            
            # Log error
            if service_name:
                self._write_to_log(service_name, log_header)
                self._write_to_log(service_name, f"ERROR: {error_msg}\n")
                self._write_to_log(service_name, log_separator)
            
            return False, error_msg, -1
            
        except PermissionError:
            error_msg = f"Permission denied executing command"
            print(f"[ExternalServicesManager] {error_msg}: {command}")
            
            # Log error
            if service_name:
                self._write_to_log(service_name, log_header)
                self._write_to_log(service_name, f"ERROR: {error_msg}\n")
                self._write_to_log(service_name, log_separator)
            
            return False, error_msg, -1
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"[ExternalServicesManager] {error_msg}: {command}")
            
            # Log error
            if service_name:
                self._write_to_log(service_name, log_header)
                self._write_to_log(service_name, f"ERROR: {error_msg}\n")
                self._write_to_log(service_name, log_separator)
            
            return False, error_msg, -1
    
    def check_health(self, service_name: str) -> Tuple[str, Optional[str]]:
        """
        Run health check command for a service
        
        Args:
            service_name: Name of the service
            
        Returns:
            Tuple of (status, error_message)
            Status: "running", "failed", "unknown"
        """
        service_def = self.get_service_definition(service_name)
        if not service_def:
            return "unknown", "Service definition not found"
        
        # Get health check command
        health_cmd = self.get_command(service_def, "health_check")
        if not health_cmd:
            return "unknown", "No health check command found"
        
        # Interpolate command
        try:
            health_cmd = self.interpolate_command(
                health_cmd,
                service_name,
                service_def
            )
        except ValueError as e:
            return "unknown", f"Configuration error: {e}"
        
        # Execute health check
        success, output, exit_code = self.execute_command(
            health_cmd,
            timeout=10,
            working_dir=service_def.working_dir,
            service_name=service_name
        )
        
        if not success:
            # Command failed to execute
            if "timed out" in output.lower():
                return "unknown", "Health check timed out"
            return "unknown", f"Health check command failed: {output}"
        
        # Check if expected string is in output
        if service_def.health_check_expected in output:
            return "running", None
        else:
            return "failed", None
    
    def install_service(
        self,
        service_name: str,
        config: Dict[str, Any],
    ) -> Tuple[bool, str, Dict[str, str]]:
        """
        Install a service with given configuration
        
        Args:
            service_name: Name of the service
            config: User configuration dictionary
            
        Returns:
            Tuple of (success, message, env_assignments)
        """
        service_def = self.get_service_definition(service_name)
        if not service_def:
            return False, f"Service {service_name} not found", {}

        user_config = dict(config)
        
        # Create service directory
        service_dir = self.services_dir / service_name
        service_dir.mkdir(parents=True, exist_ok=True)
        
        # Save configuration
        self.save_service_config(service_name, config)
        
        # Get install command
        install_cmd = self.get_command(service_def, "install")
        if not install_cmd:
            return False, f"No install command found for {service_name}", {}
        
        # Interpolate install command
        try:
            install_cmd = self.interpolate_command(
                install_cmd,
                service_name,
                service_def
            )
        except ValueError as e:
            # Missing required config variables - return error without marking as installed
            return False, str(e), {}
        
        # Execute installation
        timeout = service_def.install_timeout
        success, output, exit_code = self.execute_command(
            install_cmd,
            timeout=timeout,
            working_dir=service_def.working_dir,
            service_name=service_name
        )
        
        # Even if install fails, mark as installed so user can troubleshoot
        # Status will be unhealthy on first health check
        config_path = str(self.services_dir / service_name / "config.json")
        log_path = str(self.get_log_path(service_name))
        
        self.update_registry(service_name, {
            "installed": True,
            "installed_at": datetime.now().isoformat(),
            "enabled": False,  # Not auto-start by default
            "status": "unknown",
            "config_path": config_path,
            "log_path": log_path,
            "last_health_check": None
        })

        # Persist any derived UI routing metadata and regenerate proxy config if needed.
        self._sync_ui_route(service_name, service_def, config)

        if not success:
            return False, f"Installation command failed (exit code {exit_code}): {output}", {}

        env_assignments = self._build_env_assignments(service_name, service_def, user_config)
        if env_assignments:
            self._write_env_assignments(env_assignments)
        
        # Auto-start the service after successful installation
        print(f"[ExternalServicesManager] Auto-starting service after installation: {service_name}")
        start_success, start_msg = self.start_service(service_name)
        if not start_success:
            # Log warning but don't fail the installation
            print(f"[ExternalServicesManager] Warning: Service installed but failed to auto-start: {start_msg}")
            return True, f"Installation completed successfully (service failed to auto-start: {start_msg})", env_assignments
        
        return True, "Installation completed successfully and service started", env_assignments
    
    def uninstall_service(self, service_name: str, remove_data: bool = True) -> Tuple[bool, str]:
        """
        Uninstall a service
        
        Args:
            service_name: Name of the service
            remove_data: Whether to remove data volumes
            
        Returns:
            Tuple of (success, message)
        """
        service_def = self.get_service_definition(service_name)
        if not service_def:
            return False, f"Service {service_name} not found"
        
        # Stop the service first
        self.stop_service(service_name)
        
        # Get uninstall command
        uninstall_cmd = self.get_command(service_def, "uninstall")
        if not uninstall_cmd:
            return False, f"No uninstall command found for {service_name}"
        
        # Interpolate uninstall command
        uninstall_cmd = self.interpolate_command(
            uninstall_cmd,
            service_name,
            service_def
        )
        
        # Execute uninstallation command (best effort - handles external cleanup)
        # This might fail if Docker containers are gone, processes already stopped, etc.
        # We still proceed with Luna's cleanup regardless
        success, output, exit_code = self.execute_command(
            uninstall_cmd,
            timeout=60,
            working_dir=service_def.working_dir,
            service_name=service_name
        )
        
        if not success:
            print(f"[ExternalServicesManager] Warning: Uninstall command had issues (continuing with cleanup): {output}")
        
        # Clean up all Luna-managed files (always do this, even if uninstall cmd failed)
        
        # Remove from registry
        self.remove_from_registry(service_name)
        
        # Remove user config and data (but keep service.json)
        service_dir = self.services_dir / service_name
        
        if remove_data:
            # Remove config.json
            config_path = service_dir / "config.json"
            if config_path.exists():
                config_path.unlink()
                print(f"[ExternalServicesManager] Removed service config: {config_path}")
            
            # Remove data directory
            data_dir = service_dir / "data"
            if data_dir.exists():
                import shutil
                shutil.rmtree(data_dir)
                print(f"[ExternalServicesManager] Removed service data: {data_dir}")
            
            # Remove log file
            log_path = self.get_log_path(service_name)
            if log_path.exists():
                log_path.unlink()
                print(f"[ExternalServicesManager] Removed service log: {log_path}")
        
        # Remove entire service directory if it's an uploaded (non-bundled) service
        if not self.is_bundled_service(service_name):
            if service_dir.exists():
                import shutil
                shutil.rmtree(service_dir)
                print(f"[ExternalServicesManager] Removed uploaded service definition: {service_dir}")
        
        # Drop any UI routing metadata associated with this service.
        self._remove_ui_route(service_name)
        self._remove_env_vars(service_def.provides_vars)

        return True, "Service uninstalled successfully"
    
    def start_service(self, service_name: str) -> Tuple[bool, str]:
        """
        Start a service
        
        Args:
            service_name: Name of the service
            
        Returns:
            Tuple of (success, message)
        """
        service_def = self.get_service_definition(service_name)
        if not service_def:
            return False, f"Service {service_name} not found"
        
        # Get start command
        start_cmd = self.get_command(service_def, "start")
        if not start_cmd:
            return False, f"No start command found for {service_name}"
        
        # Interpolate start command
        try:
            start_cmd = self.interpolate_command(
                start_cmd,
                service_name,
                service_def
            )
        except ValueError as e:
            return False, f"Configuration error: {e}"
        
        # Execute start
        success, output, exit_code = self.execute_command(
            start_cmd,
            timeout=30,
            working_dir=service_def.working_dir,
            service_name=service_name
        )
        
        if not success:
            self.update_registry(service_name, {"status": "stopped"})
            return False, f"Start command failed: {output}"
        
        # Wait a bit then check health
        import time
        time.sleep(2)
        status, error = self.check_health(service_name)
        
        self.update_registry(service_name, {
            "status": status,
            "last_health_check": datetime.now().isoformat()
        })

        # If this is a Docker-based service, capture container logs
        if "docker" in start_cmd.lower():
            # Try to extract container name from command
            # Common pattern: --name container_name or luna_{service_name}
            container_name = f"luna_{service_name}"
            self.capture_docker_logs(service_name, container_name, lines=50)

        self._reload_caddy(f"start:{service_name}")
        
        return True, f"Service started (status: {status})"
    
    def stop_service(self, service_name: str) -> Tuple[bool, str]:
        """
        Stop a service
        
        Args:
            service_name: Name of the service
            
        Returns:
            Tuple of (success, message)
        """
        service_def = self.get_service_definition(service_name)
        if not service_def:
            return False, f"Service {service_name} not found"
        
        # Get stop command
        stop_cmd = self.get_command(service_def, "stop")
        if not stop_cmd:
            return False, f"No stop command found for {service_name}"
        
        # Interpolate stop command
        try:
            stop_cmd = self.interpolate_command(
                stop_cmd,
                service_name,
                service_def
            )
        except ValueError as e:
            return False, f"Configuration error: {e}"
        
        # Execute stop
        success, output, exit_code = self.execute_command(
            stop_cmd,
            timeout=30,
            working_dir=service_def.working_dir,
            service_name=service_name
        )
        
        self.update_registry(service_name, {
            "status": "stopped",
            "last_health_check": datetime.now().isoformat()
        })
        
        if not success:
            return False, f"Stop command failed: {output}"
        
        self._reload_caddy(f"stop:{service_name}")
        
        return True, "Service stopped successfully"
    
    def restart_service(self, service_name: str) -> Tuple[bool, str]:
        """
        Restart a service
        
        Args:
            service_name: Name of the service
            
        Returns:
            Tuple of (success, message)
        """
        # Stop
        stop_success, stop_msg = self.stop_service(service_name)
        
        # Wait 5 seconds
        import time
        time.sleep(5)
        
        # Start
        start_success, start_msg = self.start_service(service_name)
        
        if not start_success:
            return False, f"Restart failed: {start_msg}"
        
        self._reload_caddy(f"restart:{service_name}")
        
        return True, "Service restarted successfully"
    
    def enable_startup(self, service_name: str) -> Tuple[bool, str]:
        """
        Enable auto-start on boot for a service
        
        Args:
            service_name: Name of the service
            
        Returns:
            Tuple of (success, message)
        """
        service_def = self.get_service_definition(service_name)
        if not service_def:
            return False, f"Service {service_name} not found"
        
        # Get enable command
        enable_cmd = self.get_command(service_def, "enable_startup")
        if not enable_cmd:
            return False, f"No enable_startup command found for {service_name}"
        
        # Interpolate enable command
        enable_cmd = self.interpolate_command(
            enable_cmd,
            service_name,
            service_def
        )
        
        # Execute enable
        success, output, exit_code = self.execute_command(
            enable_cmd,
            timeout=30,
            working_dir=service_def.working_dir,
            service_name=service_name
        )
        
        self.update_registry(service_name, {"enabled": True})
        
        if not success:
            return False, f"Enable command failed: {output}"
        
        return True, "Auto-start enabled"
    
    def disable_startup(self, service_name: str) -> Tuple[bool, str]:
        """
        Disable auto-start on boot for a service
        
        Args:
            service_name: Name of the service
            
        Returns:
            Tuple of (success, message)
        """
        service_def = self.get_service_definition(service_name)
        if not service_def:
            return False, f"Service {service_name} not found"
        
        # Get disable command
        disable_cmd = self.get_command(service_def, "disable_startup")
        if not disable_cmd:
            return False, f"No disable_startup command found for {service_name}"
        
        # Interpolate disable command
        disable_cmd = self.interpolate_command(
            disable_cmd,
            service_name,
            service_def
        )
        
        # Execute disable
        success, output, exit_code = self.execute_command(
            disable_cmd,
            timeout=30,
            working_dir=service_def.working_dir,
            service_name=service_name
        )
        
        self.update_registry(service_name, {"enabled": False})
        
        if not success:
            return False, f"Disable command failed: {output}"
        
        return True, "Auto-start disabled"
    
    def is_bundled_service(self, service_name: str) -> bool:
        """
        Check if a service name is a bundled (pre-installed) service
        
        Args:
            service_name: Name of the service to check
            
        Returns:
            True if service is bundled, False otherwise
        """
        # List of bundled services that ship with Luna
        bundled_services = ["test_http_server"]  # Add more as needed
        return service_name in bundled_services
    
    def upload_service(self, service_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Upload and save a new external service definition
        
        Args:
            service_data: Service definition dictionary
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Validate service data with Pydantic
            service_def = ServiceDefinition(**service_data)
            
            # Check if name conflicts with bundled services
            if self.is_bundled_service(service_def.name):
                return False, f"Service name '{service_def.name}' conflicts with a bundled service"
            
            # Check if service already exists
            service_dir = self.services_dir / service_def.name
            if service_dir.exists():
                return False, f"Service '{service_def.name}' already exists"
            
            # Create service directory
            service_dir.mkdir(parents=True, exist_ok=True)
            
            # Write service.json
            service_json_path = service_dir / "service.json"
            with open(service_json_path, 'w') as f:
                json.dump(service_data, f, indent=2)
            
            return True, f"Service '{service_def.name}' uploaded successfully"
            
        except Exception as e:
            return False, f"Failed to upload service: {str(e)}"
