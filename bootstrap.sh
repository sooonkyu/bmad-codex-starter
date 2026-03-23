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

echo "[BMADX] project root: $PROJECT_ROOT"
echo "[BMADX] tool root: $TOOL_ROOT"
echo "[BMADX] python: $PYTHON_BIN"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[ERROR] required command not found: $1"
    exit 1
  fi
}

need_cmd bash
need_cmd git

"$PYTHON_BIN" "$TOOL_ROOT/detect_host_env.py" --project-root "$PROJECT_ROOT" --write >/dev/null || true

if ! command -v codex >/dev/null 2>&1; then
  echo "[WARN] codex CLI not found in PATH. Setup can continue, but run.py/run.sh will fail until codex is installed."
fi

if [[ ! -d _bmad ]]; then
  if [[ "${BMADX_SKIP_BMAD_INSTALL:-0}" == "1" ]]; then
    echo "[WARN] _bmad is missing and BMADX_SKIP_BMAD_INSTALL=1, so automatic BMAD install is skipped."
  elif command -v npx >/dev/null 2>&1; then
    echo "[INFO] _bmad not found. Attempting: npx bmad-method install"
    if ! npx bmad-method install; then
      echo "[WARN] Automatic BMAD install did not finish successfully."
      echo "[WARN] Complete BMAD installation manually, then rerun bootstrap.sh."
    fi
  else
    echo "[WARN] _bmad not found and npx is unavailable. Install BMAD first, then rerun bootstrap.sh."
  fi
fi

bash "$TOOL_ROOT/install.sh"

"$PYTHON_BIN" scripts/bmadx/index_bmad.py || true
"$PYTHON_BIN" scripts/bmadx/discover_env.py || true
"$PYTHON_BIN" scripts/bmadx/bootstrap_sprint_status.py || true

if [[ "${BMADX_AUTO_RUN:-0}" == "1" ]]; then
  exec bash "$TOOL_ROOT/run.sh" "$@"
fi

echo "[BMADX] bootstrap complete"
echo "[BMADX] next: python tools/bmad-codex/run.py"
