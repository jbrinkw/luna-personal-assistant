#!/usr/bin/env python3
"""
Tool Config Migration Script
Removes legacy enabled_in_mcp field from extension tool_config.json files
and deletes obsolete master_config.tool_configs section.

This is a one-time migration for the tool configuration system refactor.
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any, List


def backup_file(file_path: Path) -> Path:
    """Create a backup of a file with .backup extension"""
    backup_path = file_path.with_suffix(file_path.suffix + '.backup')
    if file_path.exists():
        import shutil
        shutil.copy2(file_path, backup_path)
        print(f"  ✓ Created backup: {backup_path}")
    return backup_path


def migrate_extension_tool_config(ext_path: Path) -> bool:
    """
    Remove enabled_in_mcp field from extension tool_config.json
    Keep other fields like passthrough, description, etc.

    Returns: True if changes were made, False if no changes
    """
    tool_config_path = ext_path / "tools" / "tool_config.json"

    if not tool_config_path.exists():
        return False

    # Load tool config
    try:
        with open(tool_config_path, 'r') as f:
            tool_config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"  ✗ ERROR: Invalid JSON in {tool_config_path}: {e}")
        return False

    # Check if any tools have enabled_in_mcp field
    changed = False
    for tool_name, tool_settings in tool_config.items():
        if isinstance(tool_settings, dict) and 'enabled_in_mcp' in tool_settings:
            del tool_settings['enabled_in_mcp']
            changed = True

    if not changed:
        return False

    # Backup original
    backup_file(tool_config_path)

    # Write updated config
    with open(tool_config_path, 'w') as f:
        json.dump(tool_config, f, indent=2)

    return True


def migrate_master_config(repo_path: Path) -> bool:
    """
    Remove tool_configs section from master_config.json

    Returns: True if changes were made, False if no changes
    """
    master_config_path = repo_path / "core" / "master_config.json"

    if not master_config_path.exists():
        print("  ✗ master_config.json not found")
        return False

    # Load master config
    try:
        with open(master_config_path, 'r') as f:
            master_config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"  ✗ ERROR: Invalid JSON in master_config.json: {e}")
        return False

    # Check if tool_configs section exists
    if 'tool_configs' not in master_config:
        return False

    tool_count = len(master_config['tool_configs'])

    # Backup original
    backup_file(master_config_path)

    # Remove tool_configs section
    del master_config['tool_configs']

    # Write updated config
    with open(master_config_path, 'w') as f:
        json.dump(master_config, f, indent=2)

    print(f"  ✓ Removed tool_configs section ({tool_count} tools)")
    return True


def discover_extensions(repo_path: Path) -> List[Path]:
    """Find all extension directories"""
    extensions_dir = repo_path / "extensions"

    if not extensions_dir.exists():
        return []

    extensions = []
    for ext_dir in extensions_dir.iterdir():
        if ext_dir.is_dir() and not ext_dir.name.startswith('.'):
            # Check if it has a tools directory
            if (ext_dir / "tools").exists():
                extensions.append(ext_dir)

    return sorted(extensions)


def main():
    """Main migration entry point"""
    print("=" * 70)
    print("Tool Configuration Migration")
    print("=" * 70)
    print()

    # Get repo path
    if len(sys.argv) > 1:
        repo_path = Path(sys.argv[1])
    else:
        # Assume running from repo root or scripts directory
        repo_path = Path(__file__).resolve().parent.parent.parent

    print(f"Repository: {repo_path}")
    print()

    if not (repo_path / "core" / "master_config.json").exists():
        print("✗ ERROR: master_config.json not found. Is this the correct repo path?")
        sys.exit(1)

    # Discover extensions
    extensions = discover_extensions(repo_path)
    print(f"Found {len(extensions)} extensions with tools")
    print()

    # Migrate extension tool configs
    print("Step 1: Migrating extension tool_config.json files...")
    print("-" * 70)
    migrated_count = 0
    skipped_count = 0

    for ext_path in extensions:
        ext_name = ext_path.name
        print(f"\n{ext_name}:")

        if migrate_extension_tool_config(ext_path):
            print(f"  ✓ Removed enabled_in_mcp fields")
            migrated_count += 1
        else:
            print(f"  - No enabled_in_mcp fields found (already clean)")
            skipped_count += 1

    print()
    print(f"Extension migration complete: {migrated_count} updated, {skipped_count} already clean")
    print()

    # Migrate master config
    print("Step 2: Migrating master_config.json...")
    print("-" * 70)

    if migrate_master_config(repo_path):
        print("  ✓ Master config migrated")
    else:
        print("  - No tool_configs section found (already clean)")

    print()
    print("=" * 70)
    print("Migration Complete!")
    print("=" * 70)
    print()
    print("Summary:")
    print(f"  • {migrated_count} extension tool configs updated")
    print(f"  • {skipped_count} extensions already clean")
    print(f"  • Backups created with .backup extension")
    print()
    print("Next steps:")
    print("  1. Review the changes in your extension tool_config.json files")
    print("  2. Verify master_config.json no longer has tool_configs section")
    print("  3. Test the Tool Manager UI to ensure it still works")
    print("  4. If everything works, you can delete the .backup files")
    print()


if __name__ == "__main__":
    main()
