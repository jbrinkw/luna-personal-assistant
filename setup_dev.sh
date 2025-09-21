#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo "[python] Creating venv and installing requirements..."
python3 -m venv .venv
. ./.venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "[node] Installing dependencies for Node services (best effort)..."
install_node_deps() {
  local dir="$1"
  if [ -f "$dir/package.json" ]; then
    echo "[node] -> $dir"
    pushd "$dir" >/dev/null
    if [ -f package-lock.json ]; then
      npm ci --silent --no-audit --fund=false || true
    else
      npm install --silent --no-audit --fund=false || true
    fi
    popd >/dev/null
  fi
}

install_node_deps extensions/coachbyte/code/node
install_node_deps extensions/coachbyte/ui
install_node_deps extensions/automation_memory/backend
install_node_deps extensions/automation_memory/ui
install_node_deps extensions/grocy/web

echo "[done] Setup complete. Activate venv with: source .venv/bin/activate"



