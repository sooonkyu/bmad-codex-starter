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
rm -rf .agents/skills/bmadx-sm .agents/skills/bmadx-pm .agents/skills/bmadx-po .agents/skills/bmadx-dev .agents/skills/bmadx-qa
rm -f .codex/agents/bmadx-sm.toml .codex/agents/bmadx-pm.toml .codex/agents/bmadx-po.toml .codex/agents/bmadx-dev.toml .codex/agents/bmadx-qa.toml
rm -f scripts/gates/discover_env_gate.sh scripts/gates/story_review_gate.sh scripts/gates/dev_gate.sh scripts/gates/qa_gate.sh
rm -f scripts/bmadx/index_bmad.py scripts/bmadx/discover_env.py scripts/bmadx/sprint_status.py scripts/bmadx/bootstrap_sprint_status.py scripts/bmadx/gate.py
rm -f .codex/config.bmadx.example.toml

echo "[BMADX] adapter files removed. AGENTS.override.md and .bmadx state were left in place intentionally."
