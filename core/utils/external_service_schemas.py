"""
Pydantic schemas for external service definitions and configuration forms
"""
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, root_validator, validator


class CommandsObject(BaseModel):
    """Schema for unified commands object in service.json"""

    install: str = Field(..., description="Installation command")
    uninstall: Optional[str] = Field(None, description="Uninstallation command")
    start: str = Field(..., description="Start service command")
    stop: str = Field(..., description="Stop service command")
    restart: Optional[str] = Field(None, description="Restart service command")
    health_check: str = Field(..., description="Health check command")
    enable_startup: Optional[str] = Field(None, description="Enable auto-start command")
    disable_startup: Optional[str] = Field(None, description="Disable auto-start command")


class ServiceUI(BaseModel):
    """
    Optional UI metadata for services that expose a web interface.
    Enables automatic reverse proxy routing and Hub UI deep links.
    """

    slug: Optional[str] = Field(
        None,
        description="Slug appended to /base_path/ for routing. Defaults to sanitized service name.",
    )
    base_path: str = Field(
        "ext_service",
        description="Base path segment for all external service UIs (without leading slash).",
        regex=r"^[A-Za-z0-9_\-\/]+$",
    )
    port: Optional[int] = Field(
        None,
        description="Explicit port to proxy. Must be provided when port_field is omitted.",
        ge=1,
        le=65535,
    )
    port_field: Optional[str] = Field(
        None,
        description="Key from the saved config.json that contains the host port.",
    )
    scheme: Literal["http", "https"] = Field(
        "http",
        description="Scheme used when constructing service URLs.",
    )
    strip_prefix: bool = Field(
        True,
        description="Whether to strip the generated prefix before proxying to the upstream service.",
    )
    enforce_trailing_slash: bool = Field(
        True,
        description="Whether requests without a trailing slash should 308 redirect to include it.",
    )
    open_mode: Literal["iframe", "new_tab"] = Field(
        "iframe",
        description="Default Hub UI open behaviour for the link/button.",
    )

    @root_validator
    def _ensure_port_source(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Either a literal port or a reference to a config field must be provided."""
        port = values.get("port")
        port_field = values.get("port_field")
        if (port is None) == (port_field is None):
            raise ValueError("Exactly one of 'port' or 'port_field' must be provided in ui configuration.")
        return values


class ServiceDefinition(BaseModel):
    """Schema for service.json - defines an external service"""

    name: str = Field(..., description="Unique identifier for the service")
    display_name: str = Field(..., description="Human-readable name for UI")
    description: str = Field(..., description="Short description for store listing")
    category: str = Field(..., description="Category for filtering (database, network, application, etc.)")

    # New unified format (optional)
    commands: Optional[CommandsObject] = Field(None, description="Unified commands object")
    config_form: Optional["ConfigForm"] = Field(None, description="Inline configuration form")
    ui: Optional[ServiceUI] = Field(None, description="Optional UI routing metadata")
    post_install_env: Optional[Dict[str, str]] = Field(
        None,
        description="Optional mapping of environment variables to template strings for .env population.",
    )

    # Legacy format (optional for backward compatibility)
    install_cmd: Optional[str] = Field(
        None, description="Command to run installation (receives config file path)"
    )
    uninstall_cmd: Optional[str] = Field(None, description="Command to clean up service")
    start_cmd: Optional[str] = Field(None, description="Command to start service")
    stop_cmd: Optional[str] = Field(None, description="Command to stop service")
    restart_cmd: Optional[str] = Field(None, description="Command to restart service")

    health_check_cmd: Optional[str] = Field(None, description="Command to check if running")
    health_check_expected: str = Field(
        ..., description="Substring to look for in health check output"
    )

    enable_startup_cmd: Optional[str] = Field(None, description="Command to enable auto-start on boot")
    disable_startup_cmd: Optional[str] = Field(None, description="Command to disable auto-start")

    required_vars: List[str] = Field(default_factory=list, description="Variables user must configure")
    provides_vars: List[str] = Field(default_factory=list, description="Variables this service makes available")

    # Additional fields
    author: Optional[str] = Field(None, description="Author or maintainer name")
    version: Optional[str] = Field(None, description="Service version")

    # Optional fields
    working_dir: Optional[str] = Field(None, description="Working directory for commands (defaults to repo root)")
    requires_sudo: bool = Field(False, description="Whether service requires sudo")
    install_timeout: int = Field(120, description="Installation timeout in seconds")

    @validator("commands", "install_cmd", always=True)
    def validate_commands_present(cls, v, values):
        """Ensure either commands object or legacy command fields are present"""
        if v is None and "commands" not in values:
            # Check if legacy fields are present
            if not values.get("install_cmd"):
                raise ValueError(
                    "Either 'commands' object or legacy command fields (install_cmd, etc.) must be present"
                )
        return v


class ConfigFormField(BaseModel):
    """Schema for a single field in config-form.json"""

    name: str = Field(..., description="Key in config.json")
    label: str = Field(..., description="Display label")
    type: Literal["text", "password", "number", "checkbox", "select"] = Field(
        ..., description="Input type"
    )
    default: Any = Field(None, description="Default value")
    required: bool = Field(True, description="Whether field is mandatory")
    help: Optional[str] = Field(None, description="Optional help text")
    options: Optional[List[str]] = Field(None, description="Array of options (for select type)")


class ConfigForm(BaseModel):
    """Schema for config-form.json - defines installation configuration form"""

    fields: List[ConfigFormField] = Field(..., description="List of form fields")


class RegistryEntry(BaseModel):
    """Schema for a single entry in the external services registry"""

    installed: bool = Field(True, description="Always true for entries in registry")
    installed_at: str = Field(..., description="ISO timestamp of installation")
    enabled: bool = Field(False, description="Whether auto-start on boot is enabled")
    status: Literal["running", "stopped", "unhealthy", "unknown"] = Field(
        ..., description="Current running status"
    )
    config_path: str = Field(..., description="Path to saved configuration")
    log_path: str = Field(..., description="Path to log file")
    last_health_check: Optional[str] = Field(None, description="ISO timestamp of last health check")
    ui: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional UI metadata persisted after installation (derived values).",
    )


# Registry is just a dict, no need for a Pydantic model
# This allows dynamic service names as keys
Registry = Dict[str, RegistryEntry]

# Update forward references for ServiceDefinition
ServiceDefinition.update_forward_refs()
