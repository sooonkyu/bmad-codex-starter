#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL_ROOT="$SCRIPT_DIR"

resolve_project_root() {
  local tool_root="$1"
  if [[ "$(basename "$tool_root")" == "bmad-codex" && "$(basename "$(dirname "$tool_root")")" == "tools" ]]; then
    (cd "$tool_root/../.." && pwd)
  else
    git -C "$tool_root" rev-parse --show-toplevel 2>/dev/null || (cd "$tool_root" && pwd)
  fi
}

PROJECT_ROOT="$(resolve_project_root "$TOOL_ROOT")"

cd "$PROJECT_ROOT"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[ERROR] required command not found: $1"
    exit 1
  fi
}

need_cmd python3
need_cmd bash

if ! command -v codex >/dev/null 2>&1; then
  echo "[WARN] codex CLI not found in PATH. Install/login first, then rerun."
  echo "       This package can finish local setup, but orchestrator execution needs codex."
fi

if [[ ! -d .git ]]; then
  echo "[WARN] current project is not a git repo root. Continuing anyway."
fi

if [[ ! -d _bmad ]]; then
  if command -v npx >/dev/null 2>&1; then
    echo "[INFO] _bmad not found. Attempting BMAD installation via npx bmad-method install"
    if ! npx bmad-method install; then
      echo "[WARN] BMAD install did not complete automatically."
      echo "       Complete BMAD installation manually, then rerun bootstrap.sh"
    fi
  else
    echo "[WARN] _bmad not found and npx is unavailable. Install BMAD first."
  fi
fi

bash "$TOOL_ROOT/install.sh"

python3 scripts/bmadx/index_bmad.py || true
python3 scripts/bmadx/discover_env.py || true
python3 scripts/bmadx/bootstrap_sprint_status.py || true

if [[ "${BMADX_AUTO_RUN:-1}" == "1" ]]; then
  if command -v codex >/dev/null 2>&1; then
    echo "[INFO] starting orchestrator"
    python3 "$TOOL_ROOT/orchestrator/main.py" "$@"
  else
    echo "[INFO] setup finished. codex CLI missing, so orchestrator was not started."
  fi
else
  echo "[INFO] setup finished. BMADX_AUTO_RUN=0 so orchestrator was not started."
fi
