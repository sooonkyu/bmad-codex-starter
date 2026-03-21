---
name: bmad-qa
description: BMAD QA verification and release gate review.
---

1. Read `AGENTS.override.md`.
2. Read `.codex/agents/qa.toml`.
3. Read `.bmadx/state/runtime-manifest.json`.
4. Verify through real command execution.
5. Write `.bmadx/reviews/<story>.qa-report.md` with PASS/FAIL.
6. Never claim pass unless the qa gate passes.
