#!/usr/bin/env python3
"""
Start all *_mcp_server.py scripts in this repository, each in its own process.

Features:
- Discovers servers recursively (default pattern: *_mcp_server.py)
- Starts each in its own process with isolated working directory
- Streams output to console (can be disabled) and writes per-server logs
- Gracefully shuts down all children on Ctrl+C / termination

Usage examples:
  python start_all_mcp_servers.py --dry-run
  python start_all_mcp_servers.py
  python start_all_mcp_servers.py --no-stream
"""

from __future__ import annotations

import argparse
import atexit
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from threading import Thread
from typing import Iterable, List, Optional, Set, Tuple


DEFAULT_EXCLUDED_DIRS: Set[str] = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".mypy_cache",
    ".pytest_cache",
    "dist",
    "build",
}


class ManagedProcess:
    """Holds a child process, label, and log file path."""

    def __init__(self, label: str, proc: subprocess.Popen, log_path: Path) -> None:
        self.label = label
        self.proc = proc
        self.log_path = log_path
        self._threads: List[Thread] = []

    def add_thread(self, t: Thread) -> None:
        self._threads.append(t)

    def is_running(self) -> bool:
        return self.proc.poll() is None


def discover_servers(
    root: Path, pattern: str, exclude_dirs: Set[str]
) -> List[Path]:
    """Find all files under root matching pattern, skipping excluded directories."""
    servers: List[Path] = []
    for path in root.rglob(pattern):
        if not path.is_file():
            continue
        # Skip if any component is in excluded set
        if any(part in exclude_dirs for part in path.parts):
            continue
        servers.append(path)
    # Stable ordering: sort by relative path
    servers.sort(key=lambda p: str(p.relative_to(root)).lower())
    return servers


def ensure_log_dir(root: Path) -> Path:
    log_dir = root / "logs" / "mcp_servers"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def log_file_for(root: Path, server_path: Path) -> Path:
    """Build a deterministic log file path for a server."""
    rel = server_path.relative_to(root)
    # Example: chefbyte__chefbyte_mcp_server.log
    # Include parent directory to avoid potential name collisions.
    parts = list(rel.parts)
    if len(parts) >= 2:
        log_stem = f"{parts[-2]}__{Path(parts[-1]).stem}"
    else:
        log_stem = Path(parts[-1]).stem
    return ensure_log_dir(root) / f"{log_stem}.log"


def _make_creation_flags_and_preexec() -> Tuple[int, Optional[object]]:
    """Platform-specific process group isolation for graceful termination."""
    creation_flags = 0
    preexec_fn = None
    if os.name == "nt":
        # New process group on Windows allows sending CTRL_BREAK_EVENT
        creation_flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        # New session on POSIX allows group termination with killpg
        preexec_fn = os.setsid  # type: ignore[assignment]
    return creation_flags, preexec_fn


def launch_server(
    server_path: Path, root: Path, stream_to_console: bool
) -> ManagedProcess:
    label = f"{server_path.parent.name}/{server_path.name}"
    cmd = [sys.executable, "-u", str(server_path)]

    creation_flags, preexec_fn = _make_creation_flags_and_preexec()

    proc = subprocess.Popen(
        cmd,
        cwd=str(server_path.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        shell=False,
        creationflags=creation_flags,
        preexec_fn=preexec_fn,  # type: ignore[arg-type]
    )

    log_path = log_file_for(root, server_path)
    log_fh = log_path.open("a", encoding="utf-8")

    managed = ManagedProcess(label=label, proc=proc, log_path=log_path)

    def pump(stream, prefix: str) -> None:
        try:
            for line in iter(stream.readline, ""):
                # Write to log
                log_fh.write(f"[{prefix}] {line}")
                log_fh.flush()
                # Optionally, mirror to console
                if stream_to_console:
                    sys.stdout.write(f"[{prefix}] {line}")
                    sys.stdout.flush()
        finally:
            try:
                stream.close()
            except Exception:
                pass

    # Threads for stdout and stderr
    t_out = Thread(
        target=pump, args=(proc.stdout, label), name=f"pump-out-{label}", daemon=True
    )
    t_err = Thread(
        target=pump,
        args=(proc.stderr, f"{label} ERR"),
        name=f"pump-err-{label}",
        daemon=True,
    )
    t_out.start()
    t_err.start()
    managed.add_thread(t_out)
    managed.add_thread(t_err)

    def close_log_when_done() -> None:
        try:
            proc.wait()
        finally:
            try:
                log_fh.flush()
            finally:
                log_fh.close()

    t_log = Thread(
        target=close_log_when_done, name=f"close-log-{label}", daemon=True
    )
    t_log.start()
    managed.add_thread(t_log)

    return managed


def terminate_process(proc: subprocess.Popen) -> None:
    """Try to gracefully stop a child process, fallback to kill."""
    if proc.poll() is not None:
        return
    if os.name == "nt":
        # Try Ctrl+Break to the new process group
        try:
            proc.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            proc.wait(timeout=6)
            return
        except Exception:
            pass
        # Fallback: terminate then kill
        try:
            proc.terminate()
            proc.wait(timeout=4)
            return
        except Exception:
            pass
        try:
            proc.kill()
        except Exception:
            pass
    else:
        try:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGTERM)
        except Exception:
            try:
                proc.terminate()
            except Exception:
                pass


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Start all *_mcp_server.py scripts in the repository",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--pattern",
        default="*_mcp_server.py",
        help="Glob pattern to discover server files",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Directory name to exclude (can be provided multiple times)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only list the servers that would be started",
    )
    parser.add_argument(
        "--no-stream",
        dest="stream",
        action="store_false",
        help="Do not mirror child output to console (logs still written)",
    )
    parser.set_defaults(stream=True)

    args = parser.parse_args(list(argv) if argv is not None else None)

    # Project root
    repo_root = Path(__file__).resolve().parents[2]
    exclude_dirs = set(DEFAULT_EXCLUDED_DIRS)
    exclude_dirs.update(args.exclude)

    # Discover from the repo root rather than current working directory,
    # so running this script from any subdirectory still finds all servers.
    servers = discover_servers(repo_root, args.pattern, exclude_dirs)

    if args.dry_run:
        print(f"Discovered {len(servers)} server(s):")
        for p in servers:
            try:
                print(f" - {p.relative_to(repo_root)}")
            except Exception:
                print(f" - {p}")
        return 0

    if not servers:
        print("No servers found.")
        return 1

    print(f"Starting {len(servers)} server(s)... Press Ctrl+C to stop.")

    managed_processes: List[ManagedProcess] = []

    def shutdown_all() -> None:
        for mp in managed_processes:
            terminate_process(mp.proc)

    # Ensure we clean up on interpreter exit
    atexit.register(shutdown_all)

    # Install signal handlers for graceful shutdown
    def handle_signal(signum, frame):  # type: ignore[no-untyped-def]
        print(f"\nReceived signal {signum}. Shutting down children...")
        shutdown_all()

    try:
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)
    except Exception:
        # Some platforms may not allow installing one or both
        pass

    for path in servers:
        # Skip legacy top-level coachbyte MCP if present; new code lives in extensions
        try:
            if path.match(str(Path.cwd() / "coachbyte" / "coachbyte_mcp_server.py")):
                continue
        except Exception:
            pass
        mp = launch_server(path, repo_root, stream_to_console=args.stream)
        managed_processes.append(mp)
        status = "running" if mp.is_running() else "stopped"
        print(
            f" - {mp.label} (pid={mp.proc.pid}) -> logs: {mp.log_path} [{status}]"
        )

    # Keep the launcher alive while any child is running
    try:
        while any(mp.is_running() for mp in managed_processes):
            time.sleep(1.0)
    except KeyboardInterrupt:
        # Redundant with signal handler, but harmless
        print("\nKeyboardInterrupt: shutting down children...")
        shutdown_all()

    print("All servers have exited. Bye.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())





