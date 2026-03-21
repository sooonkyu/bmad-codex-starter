#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL_ROOT="$SCRIPT_DIR"

resolve_project_root() {
  local tool_root="$1"
  if [[ -n "${BMADX_PROJECT_ROOT:-}" ]]; then
    printf '%s\n' "$BMADX_PROJECT_ROOT"
  elif [[ "$(basename "$tool_root")" == "bmad-codex" && "$(basename "$(dirname "$tool_root")")" == "tools" ]]; then
    (cd "$tool_root/../.." && pwd)
  else
    git -C "$tool_root" rev-parse --show-toplevel 2>/dev/null || (cd "$tool_root" && pwd)
  fi
}

PROJECT_ROOT="$(resolve_project_root "$TOOL_ROOT")"

cd "$PROJECT_ROOT"
export BMADX_PROJECT_ROOT="$PROJECT_ROOT"
export BMADX_TOOL_ROOT="$TOOL_ROOT"

if ! command -v codex >/dev/null 2>&1; then
  echo "[ERROR] codex CLI not found in PATH"
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] python3 not found in PATH"
  exit 1
fi

exec python3 "$TOOL_ROOT/orchestrator/main.py" "$@"
