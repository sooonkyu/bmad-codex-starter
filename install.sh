#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL_ROOT="${BMADX_TOOL_ROOT:-$SCRIPT_DIR}"

if [[ -n "${BMADX_PROJECT_ROOT:-}" ]]; then
  PROJECT_ROOT="$BMADX_PROJECT_ROOT"
elif git rev-parse --show-toplevel >/dev/null 2>&1; then
  PROJECT_ROOT="$(git rev-parse --show-toplevel)"
else
  PROJECT_ROOT="$(cd "$TOOL_ROOT/../.." && pwd)"
fi

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

mkdir -p .agents/skills .codex/agents .bmadx/state .bmadx/reviews .bmadx/runs scripts/bmadx scripts/gates

copy_force() {
  local src="$1"
  local dst="$2"
  cp "$src" "$dst"
  echo "updated : $dst"
}

link_force() {
  local src="$1"
  local dst="$2"
  rm -rf "$dst"
  ln -snf "$src" "$dst"
  echo "linked  : $dst -> $src"
}

append_agents_override_block() {
  local dst="$PROJECT_ROOT/AGENTS.override.md"
  local block="$TOOL_ROOT/templates/AGENTS.override.md"
  local begin='<!-- BMADX:BEGIN -->'
  if [[ -f "$dst" ]]; then
    if grep -q "$begin" "$dst"; then
      echo "skip   : AGENTS.override.md already contains BMADX block"
    else
      printf '\n\n' >> "$dst"
      cat "$block" >> "$dst"
      echo "updated : AGENTS.override.md (appended BMADX block)"
    fi
  else
    cp "$block" "$dst"
    echo "created: AGENTS.override.md"
  fi
}

append_agents_override_block

mkdir -p .codex
if [[ ! -f .codex/config.toml ]]; then
  cp "$TOOL_ROOT/templates/config.toml" .codex/config.toml
  echo "created: .codex/config.toml"
else
  cp "$TOOL_ROOT/templates/config.toml" .codex/config.bmadx.example.toml
  echo "note   : existing .codex/config.toml preserved; wrote .codex/config.bmadx.example.toml"
fi

for f in sm pm po dev qa; do
  copy_force "$TOOL_ROOT/templates/agents/bmadx-${f}.toml" "$PROJECT_ROOT/.codex/agents/bmadx-${f}.toml"
done

for role in bmadx-sm bmadx-pm bmadx-po bmadx-dev bmadx-qa; do
  link_force "$TOOL_ROOT/templates/skills/$role" "$PROJECT_ROOT/.agents/skills/$role"
done

copy_force "$TOOL_ROOT/detect_host_env.py" "$PROJECT_ROOT/scripts/bmadx/detect_host_env.py"
copy_force "$TOOL_ROOT/templates/index_bmad.py" "$PROJECT_ROOT/scripts/bmadx/index_bmad.py"
copy_force "$TOOL_ROOT/templates/discover_env.py" "$PROJECT_ROOT/scripts/bmadx/discover_env.py"
copy_force "$TOOL_ROOT/templates/sprint_status.py" "$PROJECT_ROOT/scripts/bmadx/sprint_status.py"
copy_force "$TOOL_ROOT/templates/bootstrap_sprint_status.py" "$PROJECT_ROOT/scripts/bmadx/bootstrap_sprint_status.py"
copy_force "$TOOL_ROOT/templates/gate.py" "$PROJECT_ROOT/scripts/bmadx/gate.py"

copy_force "$TOOL_ROOT/templates/discover_env_gate.sh" "$PROJECT_ROOT/scripts/gates/discover_env_gate.sh"
copy_force "$TOOL_ROOT/templates/story_review_gate.sh" "$PROJECT_ROOT/scripts/gates/story_review_gate.sh"
copy_force "$TOOL_ROOT/templates/dev_gate.sh" "$PROJECT_ROOT/scripts/gates/dev_gate.sh"
copy_force "$TOOL_ROOT/templates/code_review_gate.sh" "$PROJECT_ROOT/scripts/gates/code_review_gate.sh"
copy_force "$TOOL_ROOT/templates/qa_gate.sh" "$PROJECT_ROOT/scripts/gates/qa_gate.sh"
chmod +x "$PROJECT_ROOT/scripts/gates/"*.sh

[[ -f .bmadx/state/sessions.json ]] || echo '{}' > .bmadx/state/sessions.json
"$PYTHON_BIN" -c "from pathlib import Path; import json, os; root = Path(os.environ['BMADX_PROJECT_ROOT']).resolve(); tool = Path(os.environ['BMADX_TOOL_ROOT']).resolve(); out = root / '.bmadx' / 'state' / 'install-context.json'; out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps({'project_root': str(root), 'tool_root': str(tool)}, indent=2), encoding='utf-8'); print(f'wrote {out}')"

"$PYTHON_BIN" "$TOOL_ROOT/detect_host_env.py" --project-root "$PROJECT_ROOT" --write >/dev/null || true
"$PYTHON_BIN" scripts/bmadx/index_bmad.py || true
"$PYTHON_BIN" scripts/bmadx/discover_env.py || true
"$PYTHON_BIN" scripts/bmadx/bootstrap_sprint_status.py || true
"$PYTHON_BIN" -c "from pathlib import Path; import os, sys; root = Path(os.environ['BMADX_PROJECT_ROOT']).resolve(); sys.path.insert(0, str((root / 'scripts' / 'bmadx').resolve())); from sprint_status import locate_sprint_status; path = locate_sprint_status(root); out = root / '.bmadx' / 'state' / 'sprint-status.path'; out.write_text(str(path) if path else '', encoding='utf-8'); print(f'wrote {out}')"

echo "[BMADX] install complete"
echo "[BMADX] next: python tools/bmad-codex/run.py"
