#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL_ROOT="${BMADX_TOOL_ROOT:-$SCRIPT_DIR}"
PROJECT_ROOT="${BMADX_PROJECT_ROOT:-$(cd "$TOOL_ROOT/../.." && pwd)}"

cd "$PROJECT_ROOT"
export BMADX_PROJECT_ROOT="$PROJECT_ROOT"
export BMADX_TOOL_ROOT="$TOOL_ROOT"

find_python() {
  if command -v py >/dev/null 2>&1; then
    echo py
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    echo python3
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    echo python
    return 0
  fi
  return 1
}

PYTHON_BIN="$(find_python || true)"
if [[ -z "$PYTHON_BIN" ]]; then
  echo "[ERROR] python3/python not found in PATH"
  exit 1
fi

"$PYTHON_BIN" "$TOOL_ROOT/detect_host_env.py" --project-root "$PROJECT_ROOT" --write >/dev/null || true
exec "$PYTHON_BIN" "$TOOL_ROOT/orchestrator/main.py" "$@"
