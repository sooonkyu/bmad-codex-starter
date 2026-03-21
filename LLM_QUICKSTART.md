# LLM quickstart

## Goal

Set up this adapter in the current project root, then run it so it automatically reads BMAD status and continues the next valid step.

## Standard assumptions

- The current directory is the project root.
- This repository should live at `tools/bmad-codex`.
- BMAD project files may already exist under `_bmad/`, `_bmad-output/`, or `.bmad-ephemeral/`.

## Required sequence for a coding LLM

1. If `tools/bmad-codex` does not exist, clone this repository into that path.
2. Read `tools/bmad-codex/README.md`.
3. Run `python3 tools/bmad-codex/bootstrap.py`.
4. Read `.bmadx/state/host-env.json`.
5. Read `.bmadx/state/runtime-manifest.json`.
6. Use the detected `preferred_mode` and command arrays from `host-env.json`. Do not guess the OS.
7. If bootstrap fails, fix the problem and rerun it.
8. Run `python3 tools/bmad-codex/run.py`.
9. Let the orchestrator choose the next story from `sprint-status.yaml` automatically.

## Windows rule

If the host is Windows and `preferred_mode` is `windows-wsl`, do not run Git Bash commands directly. Let `bootstrap.py` and `run.py` delegate into WSL.

## Done criteria

- `bootstrap.py` completes successfully
- `.bmadx/state/host-env.json` exists
- `.bmadx/state/runtime-manifest.json` exists
- `.bmadx/state/planner.json` is updated during orchestration
- the active gate script exits with code 0 before claiming completion
