# bmad-codex

BMAD persona/workflow adapter for Codex-driven project automation.

Clone this repository **inside an existing project** at exactly this path:

```bash
mkdir -p tools
git clone <THIS_REPO_URL> tools/bmad-codex
```

## Recommended entrypoints

Use the Python launchers first. They detect the current host environment, write `.bmadx/state/host-env.json`, and choose the right execution path.

```bash
python3 tools/bmad-codex/bootstrap.py
python3 tools/bmad-codex/run.py
```

On Linux, macOS, or WSL, the launchers execute `bootstrap.sh` and `run.sh` natively.
On Windows, the launchers prefer **WSL delegation**. They do not try to force PowerShell or Git Bash to behave like Linux.

## Windows recommendation

On Windows, use one of these two options:

```powershell
py -3 .\tools\bmad-codex\bootstrap.py
py -3 .\tools\bmad-codex\run.py
```

or:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\bmad-codex\bootstrap.ps1
powershell -ExecutionPolicy Bypass -File .\tools\bmad-codex\run.ps1
```

Both paths try to route execution into WSL. This is the preferred Windows mode because BMAD setup, shell tooling, and Codex automation are more stable in a Linux-like runtime.

## What bootstrap installs

- `.bmadx/state/host-env.json` with detected host OS, shell, WSL availability, and preferred commands
- `.bmadx/state/runtime-manifest.json` with detected package manager and build/test commands
- `.bmadx/state/install-context.json` and `.bmadx/state/sprint-status.path`
- `.codex/agents/bmadx-*.toml`
- `.agents/skills/bmadx-*`
- `scripts/bmadx/*`
- `scripts/gates/*`
- a managed BMADX block inside `AGENTS.override.md`

Existing `bmad-*` skills are left untouched. This package installs `bmadx-*` skills to avoid collisions.

## Automatic story progression

After bootstrap, `run.py` or `run.sh` reads BMAD sprint status and moves automatically to the next valid step.

Supported status flow:

- `backlog` -> story creation (SM -> PM/PO)
- `drafted` or `ready-for-dev` -> DEV
- `in-progress` -> DEV continuation
- `review` -> QA
- `done` -> next story

Status is read from one of these locations:

- `.bmad-ephemeral/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- fallback search under common BMAD output folders

If no sprint status exists, bootstrap tries to create one from planning artifacts.

## Host environment contract

Do not make the LLM guess which OS or shell it is running under.
Instead:

1. run `bootstrap.py`
2. read `.bmadx/state/host-env.json`
3. use the recorded `preferred_mode` and command arrays
4. avoid inventing Windows/Linux/macOS-specific commands manually

This file is the source of truth for host execution choices.

## Required tools

Native Linux/macOS/WSL runtime:

- `bash`
- `python3`
- `git`
- `codex`
- optionally `npx` if `_bmad/` is missing and you want bootstrap to try `npx bmad-method install`

Windows host:

- `py -3` or `python`
- `wsl.exe`
- a working WSL distro with `bash`, `python3`, `git`, and `codex`

## Notes on Codex execution

The orchestrator reads `.bmadx/state/host-env.json` and supports `BMADX_CODEX` as an override for the Codex executable.

Example:

```bash
BMADX_CODEX=/usr/local/bin/codex python3 tools/bmad-codex/run.py
```

## One-shot prompt for coding LLMs

```text
Current directory is the project root.
If tools/bmad-codex is missing, clone <THIS_REPO_URL> into tools/bmad-codex.
Read tools/bmad-codex/README.md and tools/bmad-codex/LLM_QUICKSTART.md.
Run python3 tools/bmad-codex/bootstrap.py.
Then read .bmadx/state/host-env.json and .bmadx/state/runtime-manifest.json.
Use the recorded preferred mode and command arrays instead of guessing OS-specific commands.
If bootstrap fails, fix the problem and rerun it.
Then run python3 tools/bmad-codex/run.py.
Let the orchestrator choose the next story from sprint-status.yaml automatically.
Never mark work complete unless the corresponding gate script exits 0.
```
