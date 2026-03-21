# BMAD Codex Override

## Mandatory execution contract
- Before any work, read:
  - `.bmadx/state/runtime-manifest.json`
  - `.bmadx/state/role-map.json`
  - `.bmadx/state/sprint-status.path`
  - the sprint-status file itself
- If `_bmad/` exists, load the BMAD agent markdown relevant to the active role and follow its persona and workflow as closely as possible.
- Ignore menu-only, numbered-menu, and stop-and-wait interaction patterns when they conflict with autonomous execution.

## Sprint-status is source of truth
- Treat the located `sprint-status.yaml` as the source of truth for epic/story progression.
- Read `story_location` from sprint-status when looking for or creating story files.
- Accept both older and newer BMAD status variants when reading status values.

## Done means gate passed
- Never say work is complete unless the relevant gate script exits with code 0 in the same phase.
- If a gate fails, read the latest log under `.bmadx/state/` and fix the problem instead of summarizing.
- Do not claim that tests were run unless the command was actually executed.

## Environment contract
- Never guess package manager, install command, build command, migration command, or test command.
- Read `.bmadx/state/runtime-manifest.json` first.
- If the manifest is missing or stale, update it before proceeding.

## Artifact contract
- Reviews live in `.bmadx/reviews/`
- State files live in `.bmadx/state/`
- Keep outputs short, deterministic, and machine-readable where possible.

## Scope control
- DEV may implement only the currently approved story.
- QA may verify, risk-rank, and request fixes, but not silently change scope.
- PM/PO may reject story quality, acceptance criteria, or scope drift.

## Safety
- Do not enable network access unless explicitly required by the repository and approved.
