#!/usr/bin/env python3
"""
Config Sync Script
Synchronize user preferences from master_config to extension configs on disk
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any


def get_current_date_version() -> str:
    """Get current date in MM-DD-YY format"""
    now = datetime.now()
    return now.strftime("%m-%d-%y")


def load_master_config(repo_path: Path) -> Dict[str, Any]:
    """Load master_config.json"""
    master_config_path = repo_path / "core" / "master_config.json"
    
    if not master_config_path.exists():
        return {
            "luna": {},
            "extensions": {},
            "tool_configs": {},
            "port_assignments": {"extensions": {}, "services": {}}
        }
    
    with open(master_config_path, 'r') as f:
        return json.load(f)


def load_extension_config(ext_path: Path) -> Dict[str, Any]:
    """Load extension's config.json"""
    config_path = ext_path / "config.json"
    
    if not config_path.exists():
        return {}
    
    with open(config_path, 'r') as f:
        return json.load(f)


def save_extension_config(ext_path: Path, config: Dict[str, Any]):
    """Save extension config to disk"""
    config_path = ext_path / "config.json"
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)


def load_tool_config(ext_path: Path) -> Dict[str, Any]:
    """Load extension's tool_config.json"""
    tool_config_path = ext_path / "tools" / "tool_config.json"
    
    if not tool_config_path.exists():
        return {}
    
    with open(tool_config_path, 'r') as f:
        return json.load(f)


def save_tool_config(ext_path: Path, config: Dict[str, Any]):
    """Save tool config to disk"""
    tool_config_path = ext_path / "tools" / "tool_config.json"
    
    # Ensure tools directory exists
    tool_config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(tool_config_path, 'w') as f:
        json.dump(config, f, indent=2)


def sync_extension_config(ext_name: str, ext_path: Path, master_data: Dict[str, Any]) -> bool:
    """
    Sync extension config with master config data
    
    Generic key matching:
    - Preserve version field (never overwrite)
    - If no version, generate from current date
    - Match and overwrite keys present in both configs
    - Preserve extension keys not in master
    - Add enabled and source fields from master
    
    Returns True if synced, False if skipped
    """
    # Load extension config from disk
    ext_config = load_extension_config(ext_path)
    
    if not ext_config:
        # Extension config doesn't exist, skip
        return False
    
    # Preserve original version or generate new one
    original_version = ext_config.get("version")
    if not original_version:
        ext_config["version"] = get_current_date_version()
    
    # Get master config data for this extension
    master_ext_config = master_data.get("config", {})
    
    # Generic key matching: update matching keys
    for key, value in master_ext_config.items():
        if key != "version":  # Never overwrite version
            # Only update if key exists in extension config (don't add new keys)
            if key in ext_config:
                ext_config[key] = value
    
    # Add enabled and source from master (not from config sub-object)
    if "enabled" in master_data:
        ext_config["enabled"] = master_data["enabled"]
    if "source" in master_data:
        ext_config["source"] = master_data["source"]
    
    # Save updated config
    save_extension_config(ext_path, ext_config)
    
    return True


def sync_tool_config(ext_name: str, ext_path: Path, master_tools: Dict[str, Any]) -> bool:
    """
    Sync tool config with master tool configs
    
    Updates tool settings from master_config.tool_configs
    """
    # Load extension's tool config
    tool_config = load_tool_config(ext_path)
    
    if not tool_config:
        # No tool config file, skip
        return False
    
    # Update tools that exist in master config
    updated = False
    for tool_name, tool_settings in master_tools.items():
        if tool_name in tool_config:
            # Update this tool's settings
            tool_config[tool_name] = tool_settings
            updated = True
    
    if updated:
        save_tool_config(ext_path, tool_config)
    
    return updated


def sync_all(repo_path: Path) -> Tuple[List[str], List[str]]:
    """
    Sync all extensions
    
    Returns: (synced_list, skipped_list)
    """
    repo_path = Path(repo_path)
    extensions_dir = repo_path / "extensions"
    
    # Load master config
    master_config = load_master_config(repo_path)
    
    synced = []
    skipped = []
    
    # Iterate through extensions in master config
    for ext_name, ext_data in master_config.get("extensions", {}).items():
        ext_path = extensions_dir / ext_name
        
        # Check if extension directory exists
        if not ext_path.exists():
            print(f"Skipping {ext_name}: directory not found")
            skipped.append(ext_name)
            continue
        
        # Sync extension config
        if sync_extension_config(ext_name, ext_path, ext_data):
            print(f"Synced extension config: {ext_name}")
            synced.append(ext_name)
        else:
            print(f"Skipped {ext_name}: config.json not found")
            skipped.append(ext_name)
            continue
        
        # Sync tool config if extension has tools
        if sync_tool_config(ext_name, ext_path, master_config.get("tool_configs", {})):
            print(f"Synced tool config: {ext_name}")
    
    return synced, skipped


def main():
    """Main entry point for standalone execution"""
    if len(sys.argv) < 2:
        print("Usage: python config_sync.py /path/to/repo")
        sys.exit(1)
    
    repo_path = Path(sys.argv[1])
    
    if not repo_path.exists():
        print(f"Error: Repository path does not exist: {repo_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("Luna Config Sync")
    print("=" * 60)
    print(f"Repository: {repo_path}")
    print()
    
    synced, skipped = sync_all(repo_path)
    
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Synced: {len(synced)} extensions")
    if synced:
        for ext in synced:
            print(f"  - {ext}")
    
    print(f"Skipped: {len(skipped)} extensions")
    if skipped:
        for ext in skipped:
            print(f"  - {ext}")
    
    print("=" * 60)


if __name__ == "__main__":
    main()

