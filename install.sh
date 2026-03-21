#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL_ROOT="$(cd "$SCRIPT_DIR" && pwd)"

resolve_project_root() {
  local tool_root="$1"
  if [[ "$(basename "$tool_root")" == "bmad-codex" && "$(basename "$(dirname "$tool_root")")" == "tools" ]]; then
    (cd "$tool_root/../.." && pwd)
  else
    git -C "$tool_root" rev-parse --show-toplevel 2>/dev/null || (cd "$tool_root" && pwd)
  fi
}

package_path_from_project_root() {
  local tool_root="$1"
  if [[ "$(basename "$tool_root")" == "bmad-codex" && "$(basename "$(dirname "$tool_root")")" == "tools" ]]; then
    echo "tools/bmad-codex"
  else
    echo "."
  fi
}

PROJECT_ROOT="$(resolve_project_root "$TOOL_ROOT")"
PACKAGE_ROOT_REL="$(package_path_from_project_root "$TOOL_ROOT")"

if [[ -z "${PROJECT_ROOT}" ]]; then
  echo "프로젝트 루트를 찾지 못했습니다. repo 루트 또는 tools/bmad-codex 형태를 확인해주세요."
  exit 1
fi

cd "$PROJECT_ROOT"

mkdir -p .agents/skills
mkdir -p .codex/agents
mkdir -p .bmadx/state .bmadx/reviews .bmadx/runs
mkdir -p scripts/bmadx scripts/gates

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

link_force() {
  local src="$1"
  local dst="$2"
  ln -snf "$src" "$dst"
  echo "linked : $dst -> $src"
}

copy_if_missing "$TOOL_ROOT/templates/AGENTS.override.md" "$PROJECT_ROOT/AGENTS.override.md"
mkdir -p "$PROJECT_ROOT/.codex"
copy_if_missing "$TOOL_ROOT/templates/config.toml" "$PROJECT_ROOT/.codex/config.toml"

for f in sm pm po dev qa; do
  copy_if_missing "$TOOL_ROOT/templates/agents/${f}.toml" "$PROJECT_ROOT/.codex/agents/${f}.toml"
done

for role in bmad-sm bmad-pm bmad-po bmad-dev bmad-qa; do
  link_force "$TOOL_ROOT/templates/skills/$role" "$PROJECT_ROOT/.agents/skills/$role"
done

copy_if_missing "$TOOL_ROOT/templates/index_bmad.py"    "$PROJECT_ROOT/scripts/bmadx/index_bmad.py"
copy_if_missing "$TOOL_ROOT/templates/discover_env.py"  "$PROJECT_ROOT/scripts/bmadx/discover_env.py"
copy_if_missing "$TOOL_ROOT/templates/sprint_status.py" "$PROJECT_ROOT/scripts/bmadx/sprint_status.py"
copy_if_missing "$TOOL_ROOT/templates/bootstrap_sprint_status.py" "$PROJECT_ROOT/scripts/bmadx/bootstrap_sprint_status.py"
copy_if_missing "$TOOL_ROOT/templates/gate.py"          "$PROJECT_ROOT/scripts/bmadx/gate.py"

copy_if_missing "$TOOL_ROOT/templates/discover_env_gate.sh" "$PROJECT_ROOT/scripts/gates/discover_env_gate.sh"
copy_if_missing "$TOOL_ROOT/templates/story_review_gate.sh" "$PROJECT_ROOT/scripts/gates/story_review_gate.sh"
copy_if_missing "$TOOL_ROOT/templates/dev_gate.sh"          "$PROJECT_ROOT/scripts/gates/dev_gate.sh"
copy_if_missing "$TOOL_ROOT/templates/qa_gate.sh"           "$PROJECT_ROOT/scripts/gates/qa_gate.sh"

chmod +x "$PROJECT_ROOT/scripts/gates/"*.sh
[[ -f .bmadx/state/sessions.json ]] || echo '{}' > .bmadx/state/sessions.json

python3 scripts/bmadx/index_bmad.py || true
python3 scripts/bmadx/discover_env.py || true
python3 - <<'PY2' || true
from pathlib import Path
import sys
sys.path.insert(0, str((Path('.') / 'scripts' / 'bmadx').resolve()))
from sprint_status import locate_sprint_status
root = Path('.').resolve()
path = locate_sprint_status(root)
out = root / '.bmadx' / 'state' / 'sprint-status.path'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(str(path) if path else '', encoding='utf-8')
print(f'wrote {out}')
PY2

if [[ "$PACKAGE_ROOT_REL" == "." ]]; then
  BOOTSTRAP_CMD="bash ./bootstrap.sh"
  ORCHESTRATOR_CMD="python3 ./orchestrator/main.py"
else
  BOOTSTRAP_CMD="bash $PACKAGE_ROOT_REL/bootstrap.sh"
  ORCHESTRATOR_CMD="python3 $PACKAGE_ROOT_REL/orchestrator/main.py"
fi

echo
echo "설치 완료"
echo "자동 부트스트랩+실행: $BOOTSTRAP_CMD"
echo "자동 실행: $ORCHESTRATOR_CMD"
echo "특정 스토리 지정: $ORCHESTRATOR_CMD --story 2.1"
