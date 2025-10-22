"""
Install all Luna dependencies.
- Python packages via uv (core + extensions)
- Node.js packages via pnpm (extension UIs)
"""
import os
import sys
import subprocess
from pathlib import Path
from typing import List, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_status(message: str, status: str = "info"):
    """Print colored status message."""
    if status == "success":
        print(f"{Colors.GREEN}[OK]{Colors.END} {message}")
    elif status == "error":
        print(f"{Colors.RED}[ERROR]{Colors.END} {message}")
    elif status == "warning":
        print(f"{Colors.YELLOW}[WARN]{Colors.END} {message}")
    elif status == "info":
        print(f"{Colors.CYAN}[INFO]{Colors.END} {message}")
    else:
        print(message)


def check_uv_installed() -> bool:
    """Check if uv is installed."""
    # First check if uv is in the venv's bin directory (VIRTUAL_ENV)
    venv_path = os.getenv('VIRTUAL_ENV')
    if venv_path:
        venv_uv = Path(venv_path) / "bin" / "uv"
        if venv_uv.exists():
            try:
                result = subprocess.run(
                    [str(venv_uv), "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    print_status(f"uv found in venv: {result.stdout.strip()}", "success")
                    return True
            except Exception as e:
                print_status(f"Error checking venv uv: {e}", "error")
    
    # Next, check the active Python's prefix (works even if VIRTUAL_ENV is unset)
    sys_prefix_uv = Path(sys.prefix) / "bin" / "uv"
    if sys_prefix_uv.exists():
        try:
            result = subprocess.run(
                [str(sys_prefix_uv), "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print_status(f"uv found via sys.prefix: {result.stdout.strip()}", "success")
                return True
        except Exception as e:
            print_status(f"Error checking sys.prefix uv: {e}", "error")
    
    # Fallback: check system PATH
    try:
        result = subprocess.run(
            ["uv", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print_status(f"uv found: {result.stdout.strip()}", "success")
            return True
        else:
            return False
    except FileNotFoundError:
        return False
    except Exception as e:
        print_status(f"Error checking uv: {e}", "error")
        return False


def read_packages_from_requirements(req_file: Path) -> List[str]:
    """
    Read and parse packages from a requirements.txt file.
    
    Args:
        req_file: Path to requirements.txt
    
    Returns:
        List of package specifications
    """
    packages = []
    try:
        with open(req_file, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    packages.append(line)
    except Exception as e:
        print_status(f"Error reading {req_file}: {e}", "warning")
    return packages


def install_requirements(req_file: Path, label: str) -> Tuple[bool, str]:
    """
    Install a requirements.txt file using uv.
    
    Args:
        req_file: Path to requirements.txt
        label: Human-readable label for this installation
    
    Returns:
        Tuple of (success, message)
    """
    if not req_file.exists():
        return False, f"File not found: {req_file}"
    
    print_status(f"Installing {label}...", "info")
    
    # Read and display packages
    packages = read_packages_from_requirements(req_file)
    if packages:
        print(f"\n{Colors.BOLD}Requested packages ({len(packages)}):{Colors.END}")
        for pkg in packages:
            print(f"  • {pkg}")
        print()
    
    try:
        # Determine uv path (prefer venv, then sys.prefix, fallback to system)
        uv_cmd = "uv"
        venv_path = os.getenv('VIRTUAL_ENV')
        if venv_path:
            venv_uv = Path(venv_path) / "bin" / "uv"
            if venv_uv.exists():
                uv_cmd = str(venv_uv)
        if uv_cmd == "uv":
            sys_prefix_uv = Path(sys.prefix) / "bin" / "uv"
            if sys_prefix_uv.exists():
                uv_cmd = str(sys_prefix_uv)
        
        # Use uv with --python flag to target the active Python
        cmd = [uv_cmd, "pip", "install", "-r", str(req_file), "--python", sys.executable]
        
        # Real-time streaming: show output as it happens
        print(f"{Colors.BOLD}Running: {' '.join(cmd)}{Colors.END}\n")
        print("=" * 70)
        
        # Set proper encoding
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            timeout=300,  # 5 minutes timeout
            env=env
        )
        
        print("=" * 70)
        
        if result.returncode == 0:
            print_status(f"{label} installed successfully", "success")
            return True, "Success"
        else:
            print_status(f"{label} installation failed (exit code: {result.returncode})", "error")
            return False, f"Exit code: {result.returncode}"
    
    except subprocess.TimeoutExpired:
        msg = "Installation timed out (>5 min)"
        print_status(f"{label}: {msg}", "error")
        return False, msg
    except Exception as e:
        msg = str(e)
        print_status(f"{label}: {msg}", "error")
        return False, msg


def find_extension_requirements() -> List[Tuple[str, Path]]:
    """
    Find all extension requirements.txt files.
    
    Returns:
        List of (extension_name, requirements_path) tuples
    """
    extensions_dir = PROJECT_ROOT / "extensions"
    if not extensions_dir.exists():
        return []
    
    extension_reqs = []
    for ext_dir in extensions_dir.iterdir():
        if ext_dir.is_dir():
            req_file = ext_dir / "requirements.txt"
            if req_file.exists():
                extension_reqs.append((ext_dir.name, req_file))
    
    return extension_reqs


def find_extension_uis() -> List[Tuple[str, Path]]:
    """
    Find all extension UIs with package.json files.
    
    Returns:
        List of (extension_name, ui_directory_path) tuples
    """
    extensions_dir = PROJECT_ROOT / "extensions"
    if not extensions_dir.exists():
        return []
    
    extension_uis = []
    for ext_dir in extensions_dir.iterdir():
        if ext_dir.is_dir():
            ui_dir = ext_dir / "ui"
            package_json = ui_dir / "package.json"
            if ui_dir.exists() and package_json.exists():
                extension_uis.append((ext_dir.name, ui_dir))
    
    return extension_uis


def install_pnpm_dependencies(ui_dir: Path, label: str) -> Tuple[bool, str]:
    """
    Install Node.js dependencies using pnpm.
    
    Args:
        ui_dir: Path to UI directory containing package.json
        label: Human-readable label for this installation
    
    Returns:
        Tuple of (success, message)
    """
    package_json = ui_dir / "package.json"
    if not package_json.exists():
        return False, f"package.json not found in {ui_dir}"
    
    print_status(f"Installing {label}...", "info")
    
    try:
        # Check if pnpm is available
        pnpm_check = subprocess.run(
            ["pnpm", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if pnpm_check.returncode != 0:
            return False, "pnpm not found"
        
        print(f"\n{Colors.BOLD}Running: pnpm install{Colors.END}\n")
        print("=" * 70)
        
        result = subprocess.run(
            ["pnpm", "install"],
            cwd=str(ui_dir),
            timeout=300  # 5 minutes timeout
        )
        
        print("=" * 70)
        
        if result.returncode == 0:
            print_status(f"{label} installed successfully", "success")
            return True, "Success"
        else:
            print_status(f"{label} installation failed (exit code: {result.returncode})", "error")
            return False, f"Exit code: {result.returncode}"
    
    except subprocess.TimeoutExpired:
        msg = "Installation timed out (>5 min)"
        print_status(f"{label}: {msg}", "error")
        return False, msg
    except FileNotFoundError:
        msg = "pnpm not found in PATH"
        print_status(f"{label}: {msg}", "error")
        return False, msg
    except Exception as e:
        msg = str(e)
        print_status(f"{label}: {msg}", "error")
        return False, msg


def install_all_dependencies() -> int:
    """
    Install all dependencies (core + extensions).
    - Python packages via uv
    - Node.js packages via pnpm
    
    Returns:
        Exit code (0 = success, 1 = failure)
    """
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}Luna Dependency Installation{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}\n")
    
    # Check uv is installed
    print_status("Checking for uv package manager...", "info")
    if not check_uv_installed():
        print_status("uv is not installed", "error")
        print("\nInstall uv with:")
        print("  pip install uv")
        print("  or visit: https://github.com/astral-sh/uv")
        return 1
    
    print()
    
    # Track results
    results = []
    
    # Install core requirements
    core_req = PROJECT_ROOT / "requirements.txt"
    if core_req.exists():
        success, msg = install_requirements(core_req, "Core dependencies")
        results.append(("Core", success, msg))
    else:
        print_status("Core requirements.txt not found", "warning")
        results.append(("Core", False, "File not found"))
    
    print()
    
    # Install Hub UI dependencies
    hub_ui_dir = PROJECT_ROOT / "hub_ui"
    hub_ui_package = hub_ui_dir / "package.json"
    if hub_ui_package.exists():
        success, msg = install_pnpm_dependencies(hub_ui_dir, "Hub UI")
        results.append(("Hub UI", success, msg))
    else:
        print_status("Hub UI package.json not found", "info")
    
    print()
    
    # Install extension requirements
    extension_reqs = find_extension_requirements()
    if extension_reqs:
        print_status(f"Found {len(extension_reqs)} extension(s) with requirements", "info")
        print()
        
        for ext_name, req_file in extension_reqs:
            success, msg = install_requirements(
                req_file,
                f"Extension: {ext_name}"
            )
            results.append((ext_name, success, msg))
            print()
    else:
        print_status("No extension requirements.txt files found", "info")
        print()
    
    # Install extension UI dependencies
    extension_uis = find_extension_uis()
    if extension_uis:
        print_status(f"Found {len(extension_uis)} extension(s) with UI", "info")
        print()
        
        for ext_name, ui_dir in extension_uis:
            success, msg = install_pnpm_dependencies(
                ui_dir,
                f"Extension UI: {ext_name}"
            )
            results.append((f"{ext_name} UI", success, msg))
            print()
    else:
        print_status("No extension UIs found with package.json", "info")
        print()
    
    # Summary
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}Installation Summary:{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
    
    success_count = sum(1 for _, success, _ in results if success)
    total_count = len(results)
    
    for name, success, msg in results:
        status = f"{Colors.GREEN}OK{Colors.END}" if success else f"{Colors.RED}FAIL{Colors.END}"
        print(f"  [{status}] {name}")
        if not success:
            print(f"       {Colors.RED}{msg[:100]}{Colors.END}")
    
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
    
    if success_count == total_count:
        print(f"{Colors.BOLD}{Colors.GREEN}All dependencies installed successfully!{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}\n")
        return 0
    else:
        print(f"{Colors.BOLD}{Colors.YELLOW}Partial installation: {success_count}/{total_count} successful{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}\n")
        return 1


def main():
    """Main entry point."""
    # Print Python info
    print(f"\n{Colors.CYAN}Python executable: {sys.executable}{Colors.END}")
    print(f"{Colors.CYAN}Python version: {sys.version.split()[0]}{Colors.END}")
    
    # Check if in a virtual environment
    import os
    in_venv = (hasattr(sys, 'real_prefix') or 
               (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) or
               os.getenv('VIRTUAL_ENV') is not None)
    
    if in_venv:
        venv_path = os.getenv('VIRTUAL_ENV', sys.prefix)
        print(f"{Colors.GREEN}Virtual environment detected: {venv_path}{Colors.END}\n")
    else:
        print(f"{Colors.YELLOW}Warning: No virtual environment detected (running in system Python){Colors.END}\n")
    
    exit_code = install_all_dependencies()
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

