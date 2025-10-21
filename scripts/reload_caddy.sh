#!/bin/bash
# Reload the Caddy configuration after regenerating it.
# Safe to call even if Caddy is not running; failures are reported but ignored.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

REASON="${1:-shell-trigger}"

if ! command -v python3 >/dev/null 2>&1; then
    echo "[reload_caddy] python3 not found; skipping reload." >&2
    exit 0
fi

PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"
export PYTHONPATH

python3 -m core.utils.caddy_control reload --repo "${REPO_ROOT}" --reason "${REASON}" >/dev/null 2>&1 || true
