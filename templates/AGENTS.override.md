<!-- BMADX:BEGIN -->
# BMAD Codex Override (BMADX managed block)

## Mandatory execution contract
- Before any work, read:
  - `.bmadx/state/host-env.json`
  - `.bmadx/state/runtime-manifest.json`
  - `.bmadx/state/role-map.json`
  - relevant story/review files under `.bmadx/`
  - the active `sprint-status.yaml` file referenced in `.bmadx/state/sprint-status.path`
- If `_bmad/` exists, load the BMAD agent markdown relevant to the active role and follow its persona and workflow as closely as possible.
- Ignore menu-only, numbered-menu, and stop-and-wait interaction patterns when they conflict with autonomous execution.

## Host environment contract
- Never guess whether the host is Windows, Linux, macOS, WSL, or Git Bash.
- Read `.bmadx/state/host-env.json` first.
- Use the recorded preferred mode and command arrays instead of inventing platform-specific commands.
- On Windows, prefer WSL delegation when `preferred_mode` is `windows-wsl`.

## Done means gate passed
- Never say work is complete unless the relevant gate script exits with code 0 in the same phase.
- If a gate fails, read the latest log under `.bmadx/state/` and fix the problem instead of summarizing.
- Do not claim that tests were run unless the command was actually executed.

## Environment contract
- Never guess package manager, install command, build command, migration command, or test command.
- Read `.bmadx/state/runtime-manifest.json` first.
- If the manifest is missing or stale, update it before proceeding.

## Scope control
- DEV may implement only the currently approved story.
- QA may verify, risk-rank, and request fixes, but not silently change scope.
- PM/PO may reject story quality, acceptance criteria, or scope drift.
<!-- BMADX:END -->
