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

package_path_from_project_root() {
  local tool_root="$1"
  if [[ "$(basename "$tool_root")" == "bmad-codex" && "$(basename "$(dirname "$tool_root")")" == "tools" ]]; then
    printf '%s\n' "tools/bmad-codex"
  else
    printf '%s\n' "."
  fi
}

PROJECT_ROOT="$(resolve_project_root "$TOOL_ROOT")"
PACKAGE_ROOT_REL="$(package_path_from_project_root "$TOOL_ROOT")"

cd "$PROJECT_ROOT"
export BMADX_PROJECT_ROOT="$PROJECT_ROOT"
export BMADX_TOOL_ROOT="$TOOL_ROOT"

echo "[BMADX] project root: $PROJECT_ROOT"
echo "[BMADX] tool root: $TOOL_ROOT"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[ERROR] required command not found: $1"
    exit 1
  fi
}

need_cmd bash
need_cmd python3
need_cmd git

if ! command -v codex >/dev/null 2>&1; then
  echo "[WARN] codex CLI not found in PATH. Setup can continue, but run.sh will fail until codex is installed."
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

python3 scripts/bmadx/index_bmad.py || true
python3 scripts/bmadx/discover_env.py || true
python3 scripts/bmadx/bootstrap_sprint_status.py || true

if [[ "${BMADX_AUTO_RUN:-0}" == "1" ]]; then
  exec bash "$TOOL_ROOT/run.sh" "$@"
fi

if [[ "$PACKAGE_ROOT_REL" == "." ]]; then
  NEXT_RUN_CMD="bash ./run.sh"
else
  NEXT_RUN_CMD="bash $PACKAGE_ROOT_REL/run.sh"
fi

echo "[BMADX] bootstrap complete"
echo "[BMADX] next: $NEXT_RUN_CMD"
