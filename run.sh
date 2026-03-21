#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL_ROOT="${BMADX_TOOL_ROOT:-$SCRIPT_DIR}"
PROJECT_ROOT="${BMADX_PROJECT_ROOT:-$(cd "$TOOL_ROOT/../.." && pwd)}"

cd "$PROJECT_ROOT"
export BMADX_PROJECT_ROOT="$PROJECT_ROOT"
export BMADX_TOOL_ROOT="$TOOL_ROOT"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] python3 not found in PATH"
  exit 1
fi

python3 "$TOOL_ROOT/detect_host_env.py" --project-root "$PROJECT_ROOT" --write >/dev/null || true
exec python3 "$TOOL_ROOT/orchestrator/main.py" "$@"
