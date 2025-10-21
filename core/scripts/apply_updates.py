#!/usr/bin/env python3
"""
Apply Updates Script
Execute queued extension operations and system updates
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile
from datetime import datetime


# Global log file path (set in main)
LOG_FILE = None


def log(message):
    """Print log message to both stdout and log file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [apply_updates] {message}"
    
    # Print to stdout
    print(log_line, flush=True)
    
    # Write to log file if available
    if LOG_FILE:
        try:
            with open(LOG_FILE, 'a') as f:
                f.write(log_line + "\n")
        except Exception as e:
            print(f"Warning: Failed to write to log file: {e}")


def clean_source(source):
    """
    Clean source string by removing any markers (like #reinstall)
    These markers are added by the UI to force change detection
    """
    if not source:
        return source
    
    # Remove #reinstall or any other # markers
    if '#' in source:
        source = source.split('#')[0]
    
    return source


def phase_1_check_queue(repo_path):
    """
    Phase 1: Check for Queue
    Read update_queue.json, parse operations and master_config
    """
    log("Phase 1: Checking for queue...")
    
    queue_path = repo_path / "core" / "update_queue.json"
    
    if not queue_path.exists():
        log("ERROR: No queue found!")
        log("This script should only be called when update_queue.json exists")
        sys.exit(1)
    
    log(f"Queue found: {queue_path}")
    
    with open(queue_path, 'r') as f:
        queue_data = json.load(f)
    
    operations = queue_data.get("operations", [])
    master_config = queue_data.get("master_config", {})
    
    log(f"Found {len(operations)} operations")
    
    return operations, master_config


def phase_2_delete_operations(repo_path, operations):
    """
    Phase 2: Delete Operations
    Remove extensions marked for deletion
    """
    log("Phase 2: Processing delete operations...")
    
    extensions_dir = repo_path / "extensions"
    
    for op in operations:
        if op.get("type") == "delete":
            target = op.get("target")
            target_path = extensions_dir / target
            
            if target_path.exists():
                log(f"Deleting extension: {target}")
                shutil.rmtree(target_path)
                log(f"Deleted: {target}")
            else:
                log(f"Extension not found (skipping): {target}")


def phase_3_install_operations(repo_path, operations):
    """
    Phase 3: Install Operations
    Install new extensions from various sources
    """
    log("Phase 3: Processing install operations...")
    
    extensions_dir = repo_path / "extensions"
    extensions_dir.mkdir(parents=True, exist_ok=True)
    
    for op in operations:
        if op.get("type") == "install":
            source = op.get("source", "")
            target = op.get("target")
            
            # Clean source (remove any UI markers like #reinstall)
            source = clean_source(source)
            
            # Validate source exists
            if not source or not source.strip():
                log(f"ERROR: Cannot install {target} - no source specified")
                log(f"Skipping installation of {target}")
                continue
            
            # Skip local extensions (development/bundled extensions)
            if source == "local":
                log(f"Skipping {target}: source is 'local' (development extension)")
                continue
            
            target_path = extensions_dir / target
            
            log(f"Installing extension: {target} from {source}")
            
            if source.startswith("upload:"):
                # Extract from uploaded zip
                zip_filename = source.split(":", 1)[1]
                zip_path = Path("/tmp") / zip_filename
                
                if not zip_path.exists():
                    log(f"ERROR: Zip file not found: {zip_path}")
                    continue
                
                log(f"Extracting {zip_path} to {target_path}")
                
                # Create target directory
                target_path.mkdir(parents=True, exist_ok=True)
                
                # Extract zip
                with ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(target_path)
                
                log(f"Installed: {target}")
            
            elif source.startswith("github:"):
                # Parse GitHub source: github:user/repo or github:user/repo:path/to/subfolder
                github_parts = source.split(":", 1)[1]  # Remove "github:" prefix
                
                if ":" in github_parts:
                    # Monorepo with subpath: user/repo:path/to/subfolder
                    repo_part, subpath = github_parts.split(":", 1)
                    repo_url = f"https://github.com/{repo_part}.git"
                    
                    log(f"Cloning {repo_url} (subpath: {subpath})")
                    
                    # Clone to temp directory
                    temp_clone = Path("/tmp") / f"luna_clone_{target}"
                    if temp_clone.exists():
                        shutil.rmtree(temp_clone)
                    
                    result = subprocess.run(
                        ["git", "clone", repo_url, str(temp_clone)],
                        capture_output=True,
                        text=True,
                        cwd="/tmp"
                    )
                    
                    if result.returncode != 0:
                        log(f"ERROR: Git clone failed: {result.stderr}")
                        continue
                    
                    # Copy subpath to target
                    source_path = temp_clone / subpath
                    if not source_path.exists():
                        log(f"ERROR: Subpath not found in repo: {subpath}")
                        shutil.rmtree(temp_clone)
                        continue
                    
                    log(f"Copying {source_path} to {target_path}")
                    shutil.copytree(source_path, target_path, dirs_exist_ok=True)
                    
                    # Clean up temp
                    shutil.rmtree(temp_clone)
                    log(f"Installed: {target}")
                else:
                    # Direct repo clone: user/repo
                    repo_url = f"https://github.com/{github_parts}.git"
                    
                    log(f"Cloning {repo_url} directly to {target_path}")
                    
                    result = subprocess.run(
                        ["git", "clone", repo_url, str(target_path)],
                        capture_output=True,
                        text=True,
                        cwd="/tmp"
                    )
                    
                    if result.returncode != 0:
                        log(f"ERROR: Git clone failed: {result.stderr}")
                        continue
                    
                    log(f"Installed: {target}")
            
            else:
                log(f"Unknown source format: {source}")
                continue


def phase_4_update_operations(repo_path, operations):
    """
    Phase 4: Update Operations
    Update existing extensions
    """
    log("Phase 4: Processing update operations...")
    
    extensions_dir = repo_path / "extensions"
    
    for op in operations:
        if op.get("type") == "update":
            source = op.get("source", "")
            target = op.get("target")
            
            # Clean source (remove any UI markers like #reinstall)
            source = clean_source(source)
            
            # Validate source exists
            if not source or not source.strip():
                log(f"ERROR: Cannot update {target} - no source specified")
                log(f"Skipping update of {target}")
                continue
            
            # Skip local extensions (development/bundled extensions)
            if source == "local":
                log(f"Skipping {target}: source is 'local' (development extension, no updates)")
                continue
            
            target_path = extensions_dir / target
            
            log(f"Updating extension: {target} from {source}")
            
            if source.startswith("upload:"):
                # Remove old and install new
                if target_path.exists():
                    log(f"Removing old version: {target}")
                    shutil.rmtree(target_path)
                
                # Extract from uploaded zip
                zip_filename = source.split(":", 1)[1]
                zip_path = Path("/tmp") / zip_filename
                
                if not zip_path.exists():
                    log(f"ERROR: Zip file not found: {zip_path}")
                    continue
                
                log(f"Extracting {zip_path} to {target_path}")
                
                # Create target directory
                target_path.mkdir(parents=True, exist_ok=True)
                
                # Extract zip
                with ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(target_path)
                
                log(f"Updated: {target}")
            
            elif source.startswith("github:"):
                # Parse GitHub source: github:user/repo or github:user/repo:path/to/subfolder
                github_parts = source.split(":", 1)[1]  # Remove "github:" prefix
                
                if ":" in github_parts:
                    # Monorepo with subpath - remove and reinstall
                    repo_part, subpath = github_parts.split(":", 1)
                    repo_url = f"https://github.com/{repo_part}.git"
                    
                    log(f"Updating {target} from monorepo (remove and reinstall)")
                    
                    # Remove old version
                    if target_path.exists():
                        shutil.rmtree(target_path)
                    
                    # Clone to temp directory
                    temp_clone = Path("/tmp") / f"luna_clone_{target}"
                    if temp_clone.exists():
                        shutil.rmtree(temp_clone)
                    
                    result = subprocess.run(
                        ["git", "clone", repo_url, str(temp_clone)],
                        capture_output=True,
                        text=True,
                        cwd="/tmp"
                    )
                    
                    if result.returncode != 0:
                        log(f"ERROR: Git clone failed: {result.stderr}")
                        continue
                    
                    # Copy subpath to target
                    source_path = temp_clone / subpath
                    if not source_path.exists():
                        log(f"ERROR: Subpath not found in repo: {subpath}")
                        shutil.rmtree(temp_clone)
                        continue
                    
                    shutil.copytree(source_path, target_path, dirs_exist_ok=True)
                    
                    # Clean up temp
                    shutil.rmtree(temp_clone)
                    log(f"Updated: {target}")
                else:
                    # Direct repo - git fetch and reset
                    if not target_path.exists():
                        log(f"ERROR: Extension directory not found: {target_path}")
                        continue
                    
                    log(f"Updating {target} via git reset")
                    
                    # Fetch latest
                    result = subprocess.run(
                        ["git", "fetch", "origin"],
                        cwd=target_path,
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode != 0:
                        log(f"WARNING: Git fetch failed: {result.stderr}")
                    
                    # Reset to origin/main
                    result = subprocess.run(
                        ["git", "reset", "--hard", "origin/main"],
                        cwd=target_path,
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode != 0:
                        log(f"ERROR: Git reset failed: {result.stderr}")
                        continue
                    
                    log(f"Updated: {target}")
            
            else:
                log(f"Unknown source format: {source}")
                continue


def phase_5_core_update(repo_path, operations):
    """
    Phase 5: Core Update Operations
    Update Luna core system
    """
    log("Phase 5: Processing core update operations...")
    
    for op in operations:
        if op.get("type") == "update_core":
            target_version = op.get("target_version", "latest")
            
            log(f"Updating Luna core to {target_version}")
            log("Running: git fetch origin")
            
            # Fetch latest from origin
            result = subprocess.run(
                ["git", "fetch", "origin"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                log(f"ERROR: Git fetch failed: {result.stderr}")
                continue
            
            log("Fetch successful")
            log("Running: git reset --hard origin/main")
            
            # Reset to origin/main
            result = subprocess.run(
                ["git", "reset", "--hard", "origin/main"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                log(f"ERROR: Git reset failed: {result.stderr}")
                continue
            
            log(f"Core updated successfully to {target_version}")
            
            # Get the new commit hash for logging
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                new_commit = result.stdout.strip()[:7]
                log(f"Now at commit: {new_commit}")


def phase_6_install_dependencies(repo_path):
    """
    Phase 6: Install All Dependencies
    Install core and extension dependencies
    """
    log("Phase 6: Installing dependencies...")
    
    # Core dependencies
    log("Installing core dependencies...")
    
    core_requirements = repo_path / "requirements.txt"
    if core_requirements.exists():
        log("Installing core Python dependencies...")
        result = subprocess.run(
            ["pip", "install", "-r", str(core_requirements), "--break-system-packages"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            log(f"WARNING: Core pip install had errors: {result.stderr}")
        else:
            log("Core Python dependencies installed")
    
    hub_ui_package = repo_path / "hub_ui" / "package.json"
    if hub_ui_package.exists():
        log("Installing hub_ui dependencies...")
        
        # Try pnpm first, fall back to npm
        if shutil.which('pnpm'):
            log("Using pnpm...")
            result = subprocess.run(
                ["pnpm", "install"],
                cwd=repo_path / "hub_ui",
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                log(f"WARNING: hub_ui pnpm install had errors: {result.stderr}")
            else:
                log("hub_ui dependencies installed")
        elif shutil.which('npm'):
            log("pnpm not found, using npm...")
            result = subprocess.run(
                ["npm", "install"],
                cwd=repo_path / "hub_ui",
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                log(f"WARNING: hub_ui npm install had errors: {result.stderr}")
            else:
                log("hub_ui dependencies installed")
        else:
            log("WARNING: Neither pnpm nor npm found, skipping hub_ui dependencies")
    
    # Extension dependencies
    log("Installing extension dependencies...")
    
    extensions_dir = repo_path / "extensions"
    if extensions_dir.exists():
        for ext_dir in extensions_dir.iterdir():
            if not ext_dir.is_dir():
                continue
            
            ext_name = ext_dir.name
            
            # Extension Python dependencies
            ext_requirements = ext_dir / "requirements.txt"
            if ext_requirements.exists():
                log(f"Installing {ext_name} Python dependencies...")
                result = subprocess.run(
                    ["pip", "install", "-r", str(ext_requirements), "--break-system-packages"],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    log(f"WARNING: {ext_name} pip install had errors: {result.stderr}")
            
            # Extension UI dependencies
            ui_package = ext_dir / "ui" / "package.json"
            if ui_package.exists():
                log(f"Installing {ext_name} UI dependencies...")
                
                # Try pnpm first, fall back to npm
                if shutil.which('pnpm'):
                    result = subprocess.run(
                        ["pnpm", "install"],
                        cwd=ext_dir / "ui",
                        capture_output=True,
                        text=True
                    )
                    if result.returncode != 0:
                        log(f"WARNING: {ext_name} UI pnpm install had errors: {result.stderr}")
                    else:
                        log(f"{ext_name} UI dependencies installed")
                elif shutil.which('npm'):
                    result = subprocess.run(
                        ["npm", "install"],
                        cwd=ext_dir / "ui",
                        capture_output=True,
                        text=True
                    )
                    if result.returncode != 0:
                        log(f"WARNING: {ext_name} UI npm install had errors: {result.stderr}")
                    else:
                        log(f"{ext_name} UI dependencies installed")
                else:
                    log(f"WARNING: Neither pnpm nor npm found, skipping {ext_name} UI dependencies")
            
            # Service dependencies
            services_dir = ext_dir / "services"
            if services_dir.exists():
                for service_dir in services_dir.iterdir():
                    if not service_dir.is_dir():
                        continue
                    
                    service_requirements = service_dir / "requirements.txt"
                    if service_requirements.exists():
                        service_name = service_dir.name
                        log(f"Installing {ext_name}.{service_name} dependencies...")
                        result = subprocess.run(
                            ["pip", "install", "-r", str(service_requirements), "--break-system-packages"],
                            capture_output=True,
                            text=True
                        )
                        if result.returncode != 0:
                            log(f"WARNING: {ext_name}.{service_name} pip install had errors")
    
    log("Dependency installation complete")


def phase_7_overwrite_master_config(repo_path, master_config):
    """
    Phase 7: Overwrite Master Config
    Write queue's master_config to core/master_config.json
    """
    log("Phase 7: Overwriting master config...")
    
    master_config_path = repo_path / "core" / "master_config.json"
    
    with open(master_config_path, 'w') as f:
        json.dump(master_config, f, indent=2)
    
    log(f"Master config updated: {master_config_path}")


def phase_8_clear_queue(repo_path):
    """
    Phase 8: Clear Queue
    Delete update_queue.json, retry counter, and update flag
    """
    log("Phase 8: Clearing queue...")
    
    queue_path = repo_path / "core" / "update_queue.json"
    
    if queue_path.exists():
        queue_path.unlink()
        log("Queue cleared")
    else:
        log("Queue already cleared")
    
    # Also clear retry counter on successful completion
    retry_state_path = repo_path / "core" / "update_retry_count.json"
    if retry_state_path.exists():
        retry_state_path.unlink()
        log("Retry counter cleared")
    
    # Clear update flag so bootstrap knows update is complete
    update_flag = repo_path / ".luna_updating"
    if update_flag.exists():
        update_flag.unlink()
        log("Update flag cleared")


def phase_9_cleanup_and_exit(repo_path):
    """
    Phase 9: Cleanup and Exit
    Delete this script and exit (bootstrap is waiting and will restart supervisor)
    """
    log("Phase 9: Cleanup and exit...")
    
    # Delete this script from /tmp
    script_path = Path("/tmp/luna_apply_updates.py")
    if script_path.exists():
        script_path.unlink()
        log("Cleaned up temporary script")
    
    log("=" * 60)
    log("Updates applied successfully!")
    log("Bootstrap will now restart the supervisor...")
    log("=" * 60)
    
    # Exit cleanly - bootstrap is waiting for update flag removal and will restart supervisor
    sys.exit(0)


def main():
    """Main entry point"""
    global LOG_FILE
    
    if len(sys.argv) < 2:
        print("Usage: python apply_updates.py /path/to/repo")
        sys.exit(1)
    
    repo_path = Path(sys.argv[1])
    
    if not repo_path.exists():
        print(f"Error: Repository path does not exist: {repo_path}")
        sys.exit(1)
    
    # Initialize log file
    logs_dir = repo_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    LOG_FILE = logs_dir / "apply_updates.log"
    
    log("=" * 60)
    log("Luna Apply Updates")
    log("=" * 60)
    log(f"Repository: {repo_path}")
    log(f"Log file: {LOG_FILE}")
    log("")
    
    try:
        # Phase 1: Check for queue
        operations, master_config = phase_1_check_queue(repo_path)
        
        # Phase 2: Delete operations
        phase_2_delete_operations(repo_path, operations)
        
        # Phase 3: Install operations
        phase_3_install_operations(repo_path, operations)
        
        # Phase 4: Update operations
        phase_4_update_operations(repo_path, operations)
        
        # Phase 5: Core update
        phase_5_core_update(repo_path, operations)
        
        # Phase 6: Install dependencies
        phase_6_install_dependencies(repo_path)
        
        # Phase 7: Overwrite master config
        phase_7_overwrite_master_config(repo_path, master_config)
        
        # Phase 8: Clear queue
        phase_8_clear_queue(repo_path)
        
        # Phase 9: Cleanup and exit
        phase_9_cleanup_and_exit(repo_path)
    
    except Exception as e:
        log(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

