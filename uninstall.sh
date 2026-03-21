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

PROJECT_ROOT="$(resolve_project_root "$TOOL_ROOT")"

if [[ -z "${PROJECT_ROOT}" ]]; then
  echo "프로젝트 루트를 찾지 못했습니다."
  exit 1
fi

cd "$PROJECT_ROOT"
rm -f .agents/skills/bmad-sm .agents/skills/bmad-pm .agents/skills/bmad-po .agents/skills/bmad-dev .agents/skills/bmad-qa
rm -f .codex/agents/sm.toml .codex/agents/pm.toml .codex/agents/po.toml .codex/agents/dev.toml .codex/agents/qa.toml
rm -f scripts/bmadx/index_bmad.py scripts/bmadx/discover_env.py scripts/bmadx/sprint_status.py scripts/bmadx/gate.py
rm -f scripts/gates/discover_env_gate.sh scripts/gates/story_review_gate.sh scripts/gates/dev_gate.sh scripts/gates/qa_gate.sh
echo "연결 해제 완료. 생성된 상태 파일(.bmadx)과 AGENTS.override.md, .codex/config.toml 은 수동 확인 후 삭제하세요."
