#!/usr/bin/env python3
"""
Start all primary apps (ChefByte UI, CoachByte API, CoachByte UI, Hub, OpenAI API server)
and gracefully shut them down on exit.
"""

from __future__ import annotations

import atexit
import os
import signal
import subprocess
import sys
from pathlib import Path
from threading import Thread
from typing import List, Optional, Tuple


class ManagedProc:
    def __init__(self, label: str, popen: subprocess.Popen, log_path: Path) -> None:
        self.label = label
        self.p = popen
        self.log_path = log_path
        self.threads: List[Thread] = []

    def running(self) -> bool:
        return self.p.poll() is None

    def wait_terminated(self, timeout: float = 8.0) -> bool:
        try:
            self.p.wait(timeout=timeout)
            return True
        except Exception:
            return False


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def ensure_log_dir(root: Path) -> Path:
    d = root / "logs" / "apps"
    d.mkdir(parents=True, exist_ok=True)
    return d


def spawn(cmd: List[str], cwd: Path, env: Optional[dict] = None, label: str = "app") -> ManagedProc:
    creation_flags = 0
    preexec_fn = None
    if os.name != "nt":
        preexec_fn = os.setsid  # type: ignore[assignment]

    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        shell=False,
        creationflags=creation_flags,
        preexec_fn=preexec_fn,  # type: ignore[arg-type]
        env=env or os.environ.copy(),
    )

    log_dir = ensure_log_dir(repo_root())
    log_f = (log_dir / f"{label.replace(' ', '_')}.log").open("a", encoding="utf-8")
    mp = ManagedProc(label, proc, log_dir / f"{label.replace(' ', '_')}.log")

    def pump(stream, prefix: str) -> None:
        try:
            for line in iter(stream.readline, ""):
                log_f.write(f"[{prefix}] {line}")
                log_f.flush()
                sys.stdout.write(f"[{prefix}] {line}")
                sys.stdout.flush()
        finally:
            try:
                stream.close()
            except Exception:
                pass

    t1 = Thread(target=pump, args=(proc.stdout, label), daemon=True)
    t2 = Thread(target=pump, args=(proc.stderr, f"{label} ERR"), daemon=True)
    t1.start(); t2.start()
    mp.threads += [t1, t2]
    return mp


def terminate(p: subprocess.Popen) -> None:
    if p.poll() is not None:
        return
    if os.name == "nt":
        try:
            p.terminate()
        except Exception:
            pass
    else:
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        except Exception:
            try:
                p.terminate()
            except Exception:
                pass


def main() -> int:
    root = repo_root()

    # Ports and environment (hardcoded UI ports)
    # UI ports start at 8030 and increment per app
    chef_port = "8030"
    coach_api_port = os.getenv("COACH_API_PORT", "3001")  # API is not a UI; keep existing port
    coach_ui_port = "8031"
    hub_port = "8032"
    openai_api_port = os.getenv("OPENAI_API_PORT", "8010")

    # Define app directories
    chef_dir = root / "extensions" / "chefbyte" / "ui" / "chefbyte_webapp"
    openai_dir = root / "core" / "agent"
    coach_api_dir = root / "extensions" / "coachbyte" / "code" / "node"
    coach_ui_dir = root / "extensions" / "coachbyte" / "ui"
    hub_dir = root / "core" / "hub" / "ui_hub"

    # Expose links for hub based on availability
    agent_links = []
    if chef_dir.exists():
        agent_links.append(f"ChefByte:http://localhost:{chef_port}")
    if coach_ui_dir.exists():
        agent_links.append(f"CoachByte:http://localhost:{coach_ui_port}")
    os.environ["AGENT_LINKS"] = ",".join(agent_links)

    procs: List[ManagedProc] = []

    def shutdown_all() -> None:
        for mp in procs:
            terminate(mp.p)
        # Confirm termination and print status
        for mp in procs:
            ok = mp.wait_terminated(timeout=6.0)
            status = 'terminated' if ok else 'still running'
            print(f"[shutdown] {mp.label}: {status}")

    atexit.register(shutdown_all)

    # ChefByte UI (FastAPI)
    # Ensure repo root is importable by the app
    env_py = os.environ.copy()
    env_py["PYTHONPATH"] = f"{root}{os.pathsep}" + env_py.get("PYTHONPATH", "")
    if chef_dir.exists():
        procs.append(spawn([sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", chef_port], chef_dir, env=env_py, label="chefbyte_ui"))
    else:
        print(f"[skip] ChefByte UI directory not found: {chef_dir}")

    # OpenAI-compatible API server (FastAPI)
    if openai_dir.exists():
        procs.append(
            spawn(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "HaVa_server:app",
                    "--host",
                    "0.0.0.0",
                    "--port",
                    str(openai_api_port),
                    "--log-level",
                    "warning",
                ],
                openai_dir,
                env=env_py,
                label="openai_api_server",
            )
        )
    else:
        print(f"[skip] OpenAI API server directory not found: {openai_dir}")

    # CoachByte API (Node)
    env_api = os.environ.copy()
    env_api["PORT"] = str(coach_api_port)
    if coach_api_dir.exists():
        try:
            nm = coach_api_dir / "node_modules"
            if not nm.exists():
                print(f"[deps] Installing Node deps for coachbyte_api in {coach_api_dir}...")
                install_cmd = ["npm", "ci"] if (coach_api_dir / "package-lock.json").exists() else ["npm", "install"]
                subprocess.run(install_cmd + ["--silent", "--no-audit", "--fund=false"], cwd=str(coach_api_dir), check=False)
        except Exception as e:
            print(f"[deps] Failed to ensure deps for coachbyte_api: {e}")
        procs.append(spawn(["node", "server.js"], coach_api_dir, env=env_api, label="coachbyte_api"))
    else:
        print(f"[skip] CoachByte API directory not found: {coach_api_dir}")

    # CoachByte UI (Vite)
    env_ui = os.environ.copy()
    env_ui["COACH_API_PORT"] = str(coach_api_port)
    if coach_ui_dir.exists():
        try:
            nm = coach_ui_dir / "node_modules"
            if not nm.exists():
                print(f"[deps] Installing Node deps for coachbyte_ui in {coach_ui_dir}...")
                install_cmd = ["npm", "ci"] if (coach_ui_dir / "package-lock.json").exists() else ["npm", "install"]
                subprocess.run(install_cmd + ["--silent", "--no-audit", "--fund=false"], cwd=str(coach_ui_dir), check=False)
        except Exception as e:
            print(f"[deps] Failed to ensure deps for coachbyte_ui: {e}")
        vite_bin = coach_ui_dir / "node_modules" / "vite" / "bin" / "vite.js"
        if vite_bin.exists():
            procs.append(spawn(["node", str(vite_bin), "--host", "0.0.0.0", "--port", str(coach_ui_port)], coach_ui_dir, env=env_ui, label="coachbyte_ui"))
        else:
            procs.append(spawn(["npx", "--yes", "vite", "--host", "0.0.0.0", "--port", str(coach_ui_port)], coach_ui_dir, env=env_ui, label="coachbyte_ui"))
    else:
        print(f"[skip] CoachByte UI directory not found: {coach_ui_dir}")

    # Hub (FastAPI)
    if hub_dir.exists():
        procs.append(spawn([sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", hub_port], hub_dir, env=env_py, label="hub"))
    else:
        print(f"[skip] Hub directory not found: {hub_dir}")

    try:
        while any(mp.running() for mp in procs):
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[manager] Caught KeyboardInterrupt. Shutting down...")
        shutdown_all()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


