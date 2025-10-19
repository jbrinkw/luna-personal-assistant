"""Process management utilities for testing"""
import subprocess
import time
from typing import Optional


def get_pid(process_name: str) -> Optional[int]:
    """Get PID of process by name"""
    try:
        result = subprocess.run(
            ['pgrep', '-f', process_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip().split('\n')[0])
        return None
    except:
        return None


def is_process_running(process_name: str) -> bool:
    """Check if process is running"""
    return get_pid(process_name) is not None


def kill_process(process_name: str, signal: int = 9) -> bool:
    """Kill process by name"""
    try:
        subprocess.run(['pkill', f'-{signal}', '-f', process_name], timeout=5)
        time.sleep(1)
        return True
    except:
        return False


def start_bootstrap(repo_path: str, log_file: str) -> bool:
    """Start luna.sh bootstrap script"""
    try:
        subprocess.Popen(
            [f'{repo_path}/luna.sh'],
            stdout=open(log_file, 'w'),
            stderr=subprocess.STDOUT,
            cwd=repo_path
        )
        return True
    except:
        return False


