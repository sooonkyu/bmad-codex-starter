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

mkdir -p .agents/skills .codex/agents .bmadx/state .bmadx/reviews .bmadx/runs scripts/bmadx scripts/gates

copy_if_missing() {
  local src="$1"
  local dst="$2"
  if [[ ! -e "$dst" ]]; then
    cp "$src" "$dst"
    echo "created: $dst"
  else
    echo "skip   : $dst already exists"
  fi
}

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

copy_force "$TOOL_ROOT/templates/index_bmad.py" "$PROJECT_ROOT/scripts/bmadx/index_bmad.py"
copy_force "$TOOL_ROOT/templates/discover_env.py" "$PROJECT_ROOT/scripts/bmadx/discover_env.py"
copy_force "$TOOL_ROOT/templates/sprint_status.py" "$PROJECT_ROOT/scripts/bmadx/sprint_status.py"
copy_force "$TOOL_ROOT/templates/bootstrap_sprint_status.py" "$PROJECT_ROOT/scripts/bmadx/bootstrap_sprint_status.py"
copy_force "$TOOL_ROOT/templates/gate.py" "$PROJECT_ROOT/scripts/bmadx/gate.py"

copy_force "$TOOL_ROOT/templates/discover_env_gate.sh" "$PROJECT_ROOT/scripts/gates/discover_env_gate.sh"
copy_force "$TOOL_ROOT/templates/story_review_gate.sh" "$PROJECT_ROOT/scripts/gates/story_review_gate.sh"
copy_force "$TOOL_ROOT/templates/dev_gate.sh" "$PROJECT_ROOT/scripts/gates/dev_gate.sh"
copy_force "$TOOL_ROOT/templates/qa_gate.sh" "$PROJECT_ROOT/scripts/gates/qa_gate.sh"
chmod +x "$PROJECT_ROOT/scripts/gates/"*.sh

[[ -f .bmadx/state/sessions.json ]] || echo '{}' > .bmadx/state/sessions.json
python3 - <<'PY'
from pathlib import Path
import json, os
root = Path(os.environ['BMADX_PROJECT_ROOT']).resolve()
tool = Path(os.environ['BMADX_TOOL_ROOT']).resolve()
out = root / '.bmadx' / 'state' / 'install-context.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({'project_root': str(root), 'tool_root': str(tool)}, indent=2), encoding='utf-8')
print(f'wrote {out}')
PY

python3 scripts/bmadx/index_bmad.py || true
python3 scripts/bmadx/discover_env.py || true
python3 scripts/bmadx/bootstrap_sprint_status.py || true
python3 - <<'PY'
from pathlib import Path
import os, sys
root = Path(os.environ['BMADX_PROJECT_ROOT']).resolve()
sys.path.insert(0, str((root / 'scripts' / 'bmadx').resolve()))
from sprint_status import locate_sprint_status
path = locate_sprint_status(root)
out = root / '.bmadx' / 'state' / 'sprint-status.path'
out.write_text(str(path) if path else '', encoding='utf-8')
print(f'wrote {out}')
PY

if [[ "$PACKAGE_ROOT_REL" == "." ]]; then
  NEXT_RUN_CMD="bash ./run.sh"
else
  NEXT_RUN_CMD="bash $PACKAGE_ROOT_REL/run.sh"
fi

echo "[BMADX] install complete"
echo "[BMADX] next: $NEXT_RUN_CMD"
