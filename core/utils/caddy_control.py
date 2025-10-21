"""
Utility helpers for managing the Caddy reverse proxy configuration.

Provides a single entry point for regenerating the Caddyfile and
triggering a graceful reload of the running Caddy instance. The helper
is safe to call repeatedly and handles missing binaries or processes
gracefully so it can be wired into all lifecycle paths.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional


def _repo_root(repo_path: Optional[os.PathLike[str] | str] = None) -> Path:
    """Resolve the repository root."""
    if repo_path is not None:
        return Path(repo_path).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def _log(message: str, quiet: bool) -> None:
    """Conditionally print log messages."""
    if not quiet:
        print(f"[caddy] {message}", flush=True)


def reload_caddy(repo_path: Optional[os.PathLike[str] | str] = None, *, reason: str | None = None, quiet: bool = True) -> bool:
    """
    Regenerate the Caddyfile and ask Caddy to reload it.

    Args:
        repo_path: Optional repository root override.
        reason: Optional human-readable context for logging.
        quiet: When False, emit progress messages to stdout.

    Returns:
        True when a reload signal was delivered successfully, False otherwise.
    """
    root = _repo_root(repo_path)
    caddy_binary = shutil.which("caddy")

    if caddy_binary is None:
        _log("Caddy binary not found in PATH; skipping reload.", quiet)
        return False

    if reason:
        _log(f"Reload requested ({reason}).", quiet)

    # Ensure the config directory exists and regenerate the latest Caddyfile.
    caddy_dir = root / ".luna"
    caddy_dir.mkdir(parents=True, exist_ok=True)
    caddyfile_path = caddy_dir / "Caddyfile"

    try:
        from .caddy_config_generator import generate_caddyfile

        generate_caddyfile(root, output_path=caddyfile_path)
    except Exception as exc:  # noqa: BLE001
        _log(f"Failed to generate Caddyfile: {exc}", quiet)
        return False

    # First attempt: use the built-in reload command which talks to the admin API.
    cmd = [
        caddy_binary,
        "reload",
        "--config",
        str(caddyfile_path),
        "--adapter",
        "caddyfile",
    ]

    reload_result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(root))  # noqa: PLW1510

    if reload_result.returncode == 0:
        _log("Caddy reload succeeded.", quiet)
        return True

    _log(
        f"Caddy reload command failed (exit {reload_result.returncode}): {reload_result.stderr.strip()}",
        quiet,
    )

    # Fallback: send SIGHUP directly to any running caddy process.
    fallback = subprocess.run(
        ["pkill", "-HUP", "-f", "caddy run"],  # noqa: PLW1510
        capture_output=True,
        text=True,
    )

    if fallback.returncode == 0:
        _log("Caddy reload triggered via SIGHUP fallback.", quiet)
        return True

    if fallback.returncode == 1:
        _log("No running caddy process found during fallback reload.", quiet)
    else:
        _log(
            f"SIGHUP fallback failed (exit {fallback.returncode}): {fallback.stderr.strip()}",
            quiet,
        )

    return False


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Regenerate the Caddyfile and reload Caddy.")
    parser.add_argument(
        "action",
        choices=["reload"],
        help="Operation to perform.",
    )
    parser.add_argument(
        "--repo",
        dest="repo_path",
        help="Path to the Luna repository root (defaults to auto-detect).",
    )
    parser.add_argument(
        "--reason",
        default=None,
        help="Optional reason string for logging context.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Emit progress messages.",
    )

    args = parser.parse_args(argv)

    if args.action == "reload":
        success = reload_caddy(args.repo_path, reason=args.reason, quiet=not args.verbose)
        return 0 if success else 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

