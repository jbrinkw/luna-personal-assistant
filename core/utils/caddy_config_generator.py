"""
Caddy Configuration Generator
Dynamically generates Caddyfile based on master_config.json
"""
import json
from pathlib import Path


def generate_caddyfile(repo_path, output_path=None):
    """
    Generate Caddyfile based on master_config.json
    
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
    
    # Check if auth file exists and read hashed credentials
    # If file doesn't exist, no auth will be enabled
    auth_file = repo_path / "caddy_auth.txt"
    auth_credentials = []
    
    if auth_file.exists():
        with open(auth_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # File should contain: username hashed_password
                    auth_credentials.append(line)
    
    # Build Caddyfile content
    lines = [
        ":8443 {",
    ]
    
    # Add basic auth if credentials exist
    if auth_credentials:
        lines.extend([
            "    # Basic Authentication",
            "    basic_auth {",
        ])
        for cred in auth_credentials:
            lines.append(f"        {cred}")
        lines.extend([
            "    }",
            "    ",
        ])
    
    lines.extend([
        "    # Core services",
        "    ",
        "    # API routes (order matters - more specific first)",
        "    handle /api/agent/* {",
        "        uri strip_prefix /api/agent",
        "        reverse_proxy 127.0.0.1:8080",
        "    }",
        "    ",
        "    handle /api/mcp/* {",
        "        uri strip_prefix /api/mcp",
        "        reverse_proxy 127.0.0.1:8765",
        "    }",
        "    ",
        "    handle /api/supervisor/* {",
        "        uri strip_prefix /api/supervisor",
        "        reverse_proxy 127.0.0.1:9999",
        "    }",
        "    ",
    ])
    
    # Add extension UI routes
    extensions = master_config.get("extensions", {})
    port_assignments = master_config.get("port_assignments", {}).get("extensions", {})
    
    enabled_extensions = []
    for ext_name, ext_config in extensions.items():
        if ext_config.get("enabled", False):
            port = port_assignments.get(ext_name)
            if port:
                enabled_extensions.append((ext_name, port))
    
    if enabled_extensions:
        lines.append("    # Extension UIs")
        for ext_name, port in sorted(enabled_extensions):
            lines.extend([
                f"    handle /ext/{ext_name}/* {{",
                f"        uri strip_prefix /ext/{ext_name}",
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
        "}",
        ""  # Empty line at end
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

