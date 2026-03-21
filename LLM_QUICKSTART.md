# LLM quickstart

## Goal

Set up this adapter in the **current project root**, then run it so it automatically reads BMAD status and continues the next valid step.

The published repository itself is flat at the repo root. Inside a real target project, the recommended install path is still `tools/bmad-codex`.

## Standard assumptions

- The current directory is the project root.
- This repository should live at `tools/bmad-codex`.
- BMAD project files may already exist under `_bmad/`, `_bmad-output/`, or `.bmad-ephemeral/`.

## Steps for a coding LLM

1. If `tools/bmad-codex` does not exist, clone this repository into that path.
2. Read `tools/bmad-codex/README.md`.
3. If running on Windows PowerShell, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\bmad-codex\bootstrap.ps1
powershell -ExecutionPolicy Bypass -File .\tools\bmad-codex\run.ps1
```

4. If running on Linux/macOS/WSL, run:

```bash
bash tools/bmad-codex/bootstrap.sh
bash tools/bmad-codex/run.sh
```

5. If bootstrap fails:
   - inspect `.bmadx/state/install-context.json`
   - inspect `.bmadx/state/runtime-manifest.json`
   - inspect `.bmadx/state/sprint-status.path`
   - inspect `.bmadx/state/last-gate-*.log`
   - fix the underlying issue and rerun bootstrap

6. During execution:
   - read the BMAD sprint status file
   - automatically choose the next story/status transition
   - do real file edits and real command runs
   - do not summarize instead of acting
   - only treat a phase as complete if its gate script exits 0

## If WSL is missing on Windows

Tell the user to open an elevated PowerShell and install WSL first, then rerun the PowerShell wrapper.

## Local package repo testing

If you are already inside this package repository root rather than a target project:

```bash
bash ./bootstrap.sh
bash ./run.sh
```
