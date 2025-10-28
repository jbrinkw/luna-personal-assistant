"""
Caddy Configuration Generator
Dynamically generates Caddyfile based on master_config.json and deployment mode
"""
import json
import os
import re
from pathlib import Path

# Load .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def sanitize_label(label: str) -> str:
    """Sanitize a string to make it safe for use as a Caddy matcher label"""
    # Replace non-alphanumeric characters with underscores
    return re.sub(r'[^a-zA-Z0-9_]', '_', label)


def generate_caddyfile(repo_path, output_path=None):
    """
    Generate Caddyfile based on master_config.json and deployment mode
    
    Args:
        repo_path: Path to Luna repository root
        output_path: Optional path to write Caddyfile (defaults to .luna/Caddyfile)
    
    Returns:
        str: Generated Caddyfile content
    """
    repo_path = Path(repo_path)

    master_config_path = repo_path / "core" / "master_config.json"
    
    if output_path is None:
        output_path = repo_path / ".luna" / "Caddyfile"
    else:
        output_path = Path(output_path)
    
    # Ensure .luna directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load master config
    if not master_config_path.exists():
        raise FileNotFoundError(f"Master config not found at {master_config_path}")
    
    with open(master_config_path, 'r') as f:
        master_config = json.load(f)
    
    # Get deployment mode from master_config or environment
    deployment_mode = master_config.get("deployment_mode") or os.getenv("DEPLOYMENT_MODE", "ngrok")
    public_domain = master_config.get("public_domain") or os.getenv("PUBLIC_DOMAIN", "")
    
    # Optional shared tokens for upstream services (used when set)
    agent_api_key = os.getenv("AGENT_API_KEY", "").strip()
    supervisor_api_token = os.getenv("SUPERVISOR_API_TOKEN", "").strip()
    mcp_auth_token = os.getenv("MCP_AUTH_TOKEN", "").strip()
    
    # Determine server address based on deployment mode
    if deployment_mode == "ngrok":
        # ngrok mode: HTTP on port 8443 (ngrok handles HTTPS)
        server_address = ":8443"
    elif deployment_mode == "nip_io":
        # nip_io mode: HTTPS with auto-SSL on {IP}.nip.io
        server_address = public_domain if public_domain else ":8443"
    elif deployment_mode == "custom_domain":
        # custom_domain mode: HTTPS with auto-SSL on custom domain
        server_address = public_domain if public_domain else ":8443"
    else:
        # Fallback to ngrok mode
        server_address = ":8443"
    
    # Build Caddyfile content
    lines = [
        f"{server_address} {{",
        "    # Core services",
        "    ",
    ]
    
    lines.extend([
        "    # PUBLIC ROUTES (no authentication)",
        "    ",
        "    # Auth Service (public for OAuth flow)",
        "    handle /auth/* {",
        "        reverse_proxy 127.0.0.1:8765",
        "    }",
        "    ",
        "    # Agent API (public for programmatic access)",
        "    handle /api/agent* {",
        "        uri strip_prefix /api/agent",
    ])
    if agent_api_key:
        lines.extend([
            "        reverse_proxy 127.0.0.1:8080 {",
            f'            header_up Authorization "Bearer {agent_api_key}"',
            "        }",
        ])
    else:
        lines.append("        reverse_proxy 127.0.0.1:8080")
    lines.extend([
        "    }",
        "    ",
        "    # MCP Server OAuth discovery endpoints (public for OAuth clients)",
        "    # Rewrite to /api/.well-known/* for the MCP server",
        "    handle /.well-known/* {",
        "        # CORS headers",
        "        header Access-Control-Allow-Origin *",
        "        header Access-Control-Allow-Methods \"GET, POST, PUT, DELETE, OPTIONS\"",
        "        header Access-Control-Allow-Headers \"Authorization, Content-Type\"",
        "        header Access-Control-Allow-Credentials true",
        "        ",
        "        # Rewrite /.well-known/* to /api/.well-known/* and proxy to MCP",
        "        rewrite * /api{uri}",
        "        reverse_proxy 127.0.0.1:8766",
        "    }",
        "    ",
        "    # MCP Server and OAuth endpoints (public for AI clients)",
        "    handle /api/* {",
        "        # CORS preflight - respond immediately to OPTIONS requests",
        "        @options method OPTIONS",
        "        handle @options {",
        "            header Access-Control-Allow-Origin *",
        "            header Access-Control-Allow-Methods \"GET, POST, PUT, DELETE, OPTIONS\"",
        "            header Access-Control-Allow-Headers \"Authorization, Content-Type\"",
        "            header Access-Control-Allow-Credentials true",
        "            respond 200",
        "        }",
        "        ",
        "        # Route /api/mcp, /api/authorize, /api/token, /api/callback to MCP server",
        "        # No path stripping - ASGI app handles full paths",
        "        @mcp_routes path /api/mcp* /api/authorize* /api/token* /api/auth/* /api/register*",
        "        handle @mcp_routes {",
        "            # CORS headers for actual requests",
        "            header Access-Control-Allow-Origin *",
        "            header Access-Control-Allow-Methods \"GET, POST, PUT, DELETE, OPTIONS\"",
        "            header Access-Control-Allow-Headers \"Authorization, Content-Type\"",
        "            header Access-Control-Allow-Credentials true",
    ])
    if mcp_auth_token:
        lines.extend([
            "            reverse_proxy 127.0.0.1:8766 {",
            f'                header_up Authorization "Bearer {mcp_auth_token}"',
            "            }",
        ])
    else:
        lines.append("            reverse_proxy 127.0.0.1:8766")
    lines.extend([
        "        }",
        "    }",
        "    ",
    ])
    
    # Supervisor API
    lines.extend([
        "    # Supervisor API",
        "    handle /api/supervisor/* {",
        "        uri strip_prefix /api/supervisor",
    ])
        
    if supervisor_api_token:
        lines.extend([
            "        reverse_proxy 127.0.0.1:9999 {",
            f'            header_up Authorization "Bearer {supervisor_api_token}"',
            "        }",
        ])
    else:
        lines.append("        reverse_proxy 127.0.0.1:9999")
    lines.extend([
        "    }",
        "    ",
    ])
    
    # Load external service UI routing metadata
    service_routes = {}
    ui_routes_path = repo_path / ".luna" / "external_service_routes.json"
    if ui_routes_path.exists():
        try:
            with open(ui_routes_path, "r") as f:
                service_routes = json.load(f)
        except Exception as exc:  # noqa: BLE001
            print(f"[caddy] Warning: failed to read external service routes: {exc}")
            service_routes = {}

    # Add extension services API routes first (before UIs, for proper precedence)
    extensions = master_config.get("extensions", {})
    service_port_assignments = master_config.get("port_assignments", {}).get("services", {})
    
    enabled_extension_services = []
    for ext_name, ext_config in extensions.items():
        if ext_config.get("enabled", False):
            # Check for extension services
            for service_key, service_port in service_port_assignments.items():
                if service_key.startswith(f"{ext_name}."):
                    enabled_extension_services.append((ext_name, service_key, service_port))
    
    if enabled_extension_services:
        lines.append("    # Extension Service APIs")
        for ext_name, service_key, service_port in sorted(enabled_extension_services):
            lines.extend([
                f"    handle /api/{ext_name}/* {{",
                f"        uri strip_prefix /api/{ext_name}",
                f"        reverse_proxy 127.0.0.1:{service_port}",
                "    }",
                "    ",
            ])

    # Add extension UI routes
    port_assignments = master_config.get("port_assignments", {}).get("extensions", {})
    
    enabled_extensions = []
    for ext_name, ext_config in extensions.items():
        if ext_config.get("enabled", False):
            port = port_assignments.get(ext_name)
            if port:
                enabled_extensions.append((ext_name, port))
    
    if enabled_extensions:
        lines.append("    # Extension UIs")
        extensions_root = repo_path / "extensions"
        for ext_name, port in sorted(enabled_extensions):
            ui_dir = extensions_root / ext_name / "ui"
            is_vite_ui = (ui_dir / "vite.config.js").exists()
            
            ui_config = {}
            ext_config_path = extensions_root / ext_name / "config.json"
            if ext_config_path.exists():
                try:
                    with open(ext_config_path, 'r') as ext_cfg_fp:
                        ext_config_data = json.load(ext_cfg_fp)
                        ui_config = ext_config_data.get("ui", {}) or {}
                except Exception:
                    ui_config = {}
            
            strip_prefix = ui_config.get("strip_prefix")
            if strip_prefix is None:
                strip_prefix = not is_vite_ui
            
            enforce_trailing_slash = ui_config.get("enforce_trailing_slash")
            if enforce_trailing_slash is None:
                # Default to True for all extensions (needed for relative paths)
                enforce_trailing_slash = True
            
            if enforce_trailing_slash:
                lines.extend([
                    f"    @{ext_name}_root {{",
                    f"        path /ext/{ext_name}",
                    "    }",
                    f"    redir @{ext_name}_root /ext/{ext_name}/ 308",
                    "    ",
                ])
            
            lines.extend([
                f"    @{ext_name}_ui {{",
            ])
            if not enforce_trailing_slash:
                lines.append(f"        path /ext/{ext_name}")
            lines.extend([
                f"        path /ext/{ext_name}/*",
                "    }",
                f"    handle @{ext_name}_ui {{",
            ])
            
            if strip_prefix:
                lines.append(f"        uri strip_prefix /ext/{ext_name}")
            
            lines.extend([
                f"        reverse_proxy 127.0.0.1:{port}",
                "    }",
                "    ",
            ])

    # Add external service UI routes
    if service_routes:
        lines.append("    # External service UIs")
        for service_name, metadata in sorted(service_routes.items(), key=lambda item: item[1].get("path", item[0])):
            port = metadata.get("port")
            path = metadata.get("path")
            if not port or not path:
                continue

            strip_prefix = metadata.get("strip_prefix", True)
            enforce_trailing_slash = metadata.get("enforce_trailing_slash", True)
            matcher_label = sanitize_label(metadata.get("slug") or service_name)
            base_path = path.rstrip("/")
            if enforce_trailing_slash:
                lines.extend([
                    f"    @{matcher_label}_svc_root {{",
                    f"        path {base_path}",
                    "    }",
                    f"    redir @{matcher_label}_svc_root {base_path}/ 308",
                    "    ",
                ])

            if strip_prefix:
                # Use handle_path which automatically strips prefix AND rewrites Location headers
                lines.extend([
                    f"    handle_path {base_path}/* {{",
                    f"        reverse_proxy 127.0.0.1:{port}",
                    "    }",
                    "    ",
                ])
            else:
                # Don't strip prefix - pass full path to service
                lines.extend([
                    f"    @{matcher_label}_svc {{",
                    f"        path {base_path}/*",
                    "    }",
                    f"    handle @{matcher_label}_svc {{",
                    f"        reverse_proxy 127.0.0.1:{port}",
                    "    }",
                    "    ",
                ])

    # Hub UI must be last (catch-all)
    lines.extend([
        "    # Hub UI (catch-all, must be last)",
        "    handle /* {",
        "        reverse_proxy 127.0.0.1:5173",
        "    }",
        "}"
    ])
    
    caddyfile_content = "\n".join(lines)
    
    # Write to file
    with open(output_path, 'w') as f:
        f.write(caddyfile_content)
    
    return caddyfile_content


if __name__ == "__main__":
    import sys
    
    repo_path = sys.argv[1] if len(sys.argv) > 1 else "."
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        content = generate_caddyfile(repo_path, output_path)
        print("Generated Caddyfile:")
        print(content)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
