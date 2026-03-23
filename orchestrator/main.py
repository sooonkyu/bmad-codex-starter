#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def find_project_root() -> Path:
    env_root = os.environ.get("BMADX_PROJECT_ROOT")
    if env_root:
        return Path(env_root).resolve()
    candidates = [Path.cwd(), Path(__file__).resolve()]
    for start in candidates:
        base_path = start if start.is_dir() else start.parent
        for base in [base_path, *base_path.parents]:
            marker = base / ".bmadx" / "state" / "install-context.json"
            if marker.exists():
                try:
                    data = json.loads(marker.read_text(encoding="utf-8"))
                    project_root = data.get("project_root")
                    if project_root:
                        return Path(project_root).resolve()
                except Exception:
                    pass
            if (base / "tools" / "bmad-codex").exists() and (base / ".bmadx").exists():
                return base.resolve()
    return Path(__file__).resolve().parents[3]


ROOT = find_project_root()
STATE = ROOT / ".bmadx" / "state"
ORCHESTRATION_STATE = STATE / "orchestration-state.json"
SESSIONS = STATE / "sessions.json"
REVIEWS = ROOT / ".bmadx" / "reviews"

STORY_VALIDATION_MAX_ATTEMPTS = 2
DEV_CYCLE_MAX_ATTEMPTS = 2

ROLE_DEVELOPER_INSTRUCTIONS = {
    "sm": "You are the BMADX scrum-master role. Read AGENTS.override.md, .bmadx/state/host-env.json, .bmadx/state/orchestration-state.json, .bmadx/state/role-map.json, .bmadx/state/runtime-manifest.json, and the active sprint status first. Load the mapped BMAD markdown and follow it closely. Do real file edits and real command runs. Never claim success unless the relevant gate can pass.",
    "pm": "You are the BMADX product-manager role. Read AGENTS.override.md, .bmadx/state/host-env.json, .bmadx/state/orchestration-state.json, .bmadx/state/role-map.json, .bmadx/state/runtime-manifest.json, and the active sprint status first. Load the mapped BMAD markdown and follow it closely. Write actionable review findings in Korean. Never approve unclear or untestable work.",
    "po": "You are the BMADX product-owner role. Read AGENTS.override.md, .bmadx/state/host-env.json, .bmadx/state/orchestration-state.json, .bmadx/state/role-map.json, .bmadx/state/runtime-manifest.json, and the active sprint status first. Load the mapped BMAD markdown and follow it closely. Write actionable review findings in Korean. Never approve scope drift or weak acceptance criteria.",
    "dev": "You are the BMADX developer role. Read AGENTS.override.md, .bmadx/state/host-env.json, .bmadx/state/orchestration-state.json, .bmadx/state/role-map.json, .bmadx/state/runtime-manifest.json, and the active sprint status first. Load the mapped BMAD markdown and follow it closely. Implement only the active story, run manifest-derived commands, and never claim success unless the relevant gate passes.",
    "qa": "You are the BMADX QA role. Read AGENTS.override.md, .bmadx/state/host-env.json, .bmadx/state/orchestration-state.json, .bmadx/state/role-map.json, .bmadx/state/runtime-manifest.json, and the active sprint status first. Load the mapped BMAD markdown and follow it closely. Perform adversarial review in Korean, demand exact file and line references for failures, run real verification commands, and never claim success unless the relevant gate passes.",
}

sys.path.insert(0, str(ROOT / "scripts" / "bmadx"))
from sprint_status import load_sprint_status, locate_sprint_status, choose_next_action, write_status, resolve_story_file, story_location_path


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def default_orchestration_state() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "current": {
            "story_key": None,
            "phase": None,
            "phase_status": "idle",
            "attempt": 0,
            "updated_at": None,
            "next_action": "",
            "notes": "",
        },
        "attempts": {
            "story_validation": {},
            "dev_cycle": {},
        },
        "history": [],
    }


def load_orchestration_state() -> dict[str, Any]:
    return read_json(ORCHESTRATION_STATE, default_orchestration_state())


def save_orchestration_state(data: dict[str, Any]) -> None:
    write_json(ORCHESTRATION_STATE, data)


def current_phase_state() -> dict[str, Any]:
    data = load_orchestration_state()
    return data.get("current", {})


def set_phase_state(
    story_key: str | None,
    phase: str | None,
    phase_status: str,
    attempt: int,
    notes: str = "",
    next_action: str = "",
) -> None:
    data = load_orchestration_state()
    data["current"] = {
        "story_key": story_key,
        "phase": phase,
        "phase_status": phase_status,
        "attempt": attempt,
        "updated_at": utc_now(),
        "next_action": next_action,
        "notes": notes,
    }
    save_orchestration_state(data)


def append_phase_history(story_key: str | None, phase: str | None, result: str, notes: str = "") -> None:
    data = load_orchestration_state()
    history = data.setdefault("history", [])
    history.append(
        {
            "timestamp": utc_now(),
            "story_key": story_key,
            "phase": phase,
            "result": result,
            "notes": notes,
        }
    )
    data["history"] = history[-200:]
    save_orchestration_state(data)


def attempt_counter(kind: str, story_key: str) -> int:
    data = load_orchestration_state()
    return int(data.get("attempts", {}).get(kind, {}).get(story_key, 0))


def phase_attempt(kind: str, story_key: str) -> int:
    return attempt_counter(kind, story_key) + 1


def bump_attempt(kind: str, story_key: str) -> int:
    data = load_orchestration_state()
    counters = data.setdefault("attempts", {}).setdefault(kind, {})
    counters[story_key] = int(counters.get(story_key, 0)) + 1
    save_orchestration_state(data)
    return counters[story_key]


def reset_attempt(kind: str, story_key: str) -> None:
    data = load_orchestration_state()
    counters = data.setdefault("attempts", {}).setdefault(kind, {})
    counters.pop(story_key, None)
    save_orchestration_state(data)


def host_env() -> dict[str, Any]:
    return read_json(STATE / "host-env.json", {})


def python_cmd() -> list[str]:
    he = host_env()
    cmd = he.get("execution", {}).get("python_cmd")
    if isinstance(cmd, list) and cmd:
        return cmd
    return [sys.executable or "python3"]


def bash_prefix() -> list[str]:
    he = host_env()
    cmd = he.get("execution", {}).get("bash_cmd")
    if isinstance(cmd, list) and cmd:
        return cmd
    return ["bash"]


def codex_cmd() -> list[str]:
    override = os.environ.get("BMADX_CODEX", "").strip()
    if override:
        return shlex.split(override)
    he = host_env()
    cmd = he.get("execution", {}).get("codex_cmd")
    if isinstance(cmd, list) and cmd:
        return cmd
    return ["codex"]


def windows_to_wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    tail = resolved.as_posix().split(":", 1)[-1].lstrip("/")
    if drive:
        return f"/mnt/{drive}/{tail}"
    return resolved.as_posix()


def extract_wsl_inner_command(cmd: list[str]) -> list[str]:
    if not cmd:
        return cmd
    if cmd[0].lower() not in {"wsl.exe", "wsl"}:
        return cmd
    if "--" in cmd:
        return cmd[cmd.index("--") + 1 :]
    return cmd[1:]


def wrap_wsl_command(cmd: list[str]) -> list[str]:
    he = host_env()
    if he.get("preferred_mode") != "windows-wsl":
        return cmd
    distro = he.get("wsl", {}).get("usable_distro")
    if not distro:
        return cmd
    inner = extract_wsl_inner_command(cmd)
    project_wsl = windows_to_wsl_path(ROOT)
    shell_command = f"cd {shlex.quote(project_wsl)} && " + " ".join(shlex.quote(part) for part in inner)
    return ["wsl.exe", "-d", distro, "--", "bash", "-lc", shell_command]


def command_available(token: str) -> bool:
    if token.lower() in ("wsl.exe", "wsl"):
        return shutil.which(token) is not None
    if any(sep in token for sep in ("/", "\\")):
        return Path(token).exists()
    return shutil.which(token) is not None


def run_process(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(wrap_wsl_command(cmd), cwd=ROOT, capture_output=True, text=True)


def run_local(cmd: list[str]) -> tuple[int, str]:
    proc = run_process(cmd)
    out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode, out


def must(cmd: list[str]) -> None:
    rc, out = run_local(cmd)
    if rc != 0:
        print(out)
        raise SystemExit(rc)


def ensure_state() -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    REVIEWS.mkdir(parents=True, exist_ok=True)
    if not SESSIONS.exists():
        write_json(SESSIONS, {})
    if not ORCHESTRATION_STATE.exists():
        save_orchestration_state(default_orchestration_state())
    must([*python_cmd(), "scripts/bmadx/index_bmad.py"])
    must([*bash_prefix(), "scripts/gates/discover_env_gate.sh"])
    must([*python_cmd(), "scripts/bmadx/bootstrap_sprint_status.py"])
    sprint = locate_sprint_status(ROOT)
    (STATE / "sprint-status.path").write_text(str(sprint) if sprint else "", encoding="utf-8")


def load_sessions() -> dict[str, str]:
    return read_json(SESSIONS, {})


def save_sessions(data: dict[str, str]) -> None:
    write_json(SESSIONS, data)


def role_exec_overrides(role: str) -> list[str]:
    instructions = ROLE_DEVELOPER_INSTRUCTIONS[role]
    return ["-m", "gpt-5.4", "-c", f"developer_instructions={json.dumps(instructions, ensure_ascii=False)}"]


def codex_exec(role: str, prompt: str) -> tuple[int, str]:
    base = codex_cmd()
    if not command_available(base[0]):
        return 127, f"codex CLI not found: {base[0]}"
    sessions = load_sessions()
    session_id = sessions.get(role)
    common = [
        *role_exec_overrides(role),
        "--json",
        "--full-auto",
        "--sandbox",
        "workspace-write",
        "--cd",
        str(ROOT),
    ]
    if session_id:
        cmd = [*base, "exec", *common, "resume", session_id, prompt]
    else:
        cmd = [*base, "exec", *common, prompt]
    proc = run_process(cmd)
    raw = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    (STATE / f"last-codex-{role}.raw.log").write_text(raw, encoding="utf-8")

    new_thread_id = None
    final_texts: list[str] = []
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("type") == "thread.started":
            new_thread_id = obj.get("thread_id")
        item = obj.get("item") or {}
        if item.get("type") == "agent_message":
            text = item.get("text")
            if text:
                final_texts.append(text)
    if new_thread_id:
        sessions[role] = new_thread_id
        save_sessions(sessions)
    return proc.returncode, "\n\n".join(final_texts).strip() or raw.strip()


def role_map() -> dict:
    return read_json(STATE / "role-map.json", {"agents": {}, "workflow_roots": []})


def common_preamble(role: str, story_key: str) -> str:
    mapped = role_map()
    agent_md = mapped.get("agents", {}).get(role)
    workflow_roots = mapped.get("workflow_roots", [])
    he = host_env()
    orchestration = load_orchestration_state().get("current", {})
    spath, data = load_sprint_status(ROOT)
    story_file = resolve_story_file(ROOT, data, story_key) if spath else None
    story_dir = story_location_path(ROOT, data) if spath else ROOT / "_bmad-output/planning-artifacts/stories"
    return f"""
Repository root: {ROOT}
Host environment: {json.dumps(he, ensure_ascii=False)}
Orchestration state: {json.dumps(orchestration, ensure_ascii=False)}
Sprint status file: {spath}
Story location directory: {story_dir}
Current target story key: {story_key}
Existing story file: {story_file}

Mandatory steps:
1. Read AGENTS.override.md
2. Read .bmadx/state/host-env.json
3. Read .bmadx/state/orchestration-state.json
4. Read .bmadx/state/runtime-manifest.json
5. Read .bmadx/state/role-map.json
6. Read .bmadx/state/sprint-status.path and then the sprint-status file itself
7. Load the BMAD agent markdown for role '{role}': {agent_md}
8. If the agent markdown references workflow files, load them. If paths are broken, search neighboring workflow roots under: {workflow_roots}
9. Do real file edits and real command runs. Do not only describe what should happen.
10. Never claim this phase is complete unless the relevant gate can pass.
"""


def sm_story_prompt(story_key: str, revise: bool) -> str:
    objective = "Revise the BMAD story using the latest PM/PO feedback." if revise else "Create the BMAD story from planning artifacts."
    extra = f"- Read `.bmadx/reviews/{story_key}.pm-review.md` and `.bmadx/reviews/{story_key}.po-review.md` before changing the story.\n" if revise else ""
    return common_preamble("sm", story_key) + f"""
Role objective:
- {objective}

Instructions:
- Find the story details for '{story_key}' in `_bmad-output/planning-artifacts/epics/` or nearby planning artifacts.
- Create or update the actual BMAD story file under the story_location path from sprint-status.
- Keep the story aligned with BMAD style as closely as possible.
- Ensure the story file includes concrete sections for Story, Acceptance Criteria, Tasks, Dev Notes, and Dev Agent Record.
- Do not write volatile "current phase", "current sprint status", or other live state claims into the persistent story unless they are clearly labeled as a temporary snapshot.
- Prefer durable instructions, durable scope, durable acceptance criteria, and durable verification steps over status narration.
{extra}- Do not approve the story yourself.
"""


def pm_prompt(story_key: str) -> str:
    return common_preamble("pm", story_key) + f"""
Review the current story for '{story_key}' as PM.
Write `.bmadx/reviews/{story_key}.pm-review.md` with this exact header:
Approved: YES or Approved: NO
Then include concise reasons and required changes in Korean.
Approve only if the story is clear, implementable, and testable.
"""


def po_prompt(story_key: str) -> str:
    return common_preamble("po", story_key) + f"""
Review the current story for '{story_key}' as PO.
Write `.bmadx/reviews/{story_key}.po-review.md` with this exact header:
Approved: YES or Approved: NO
Then include concise reasons and required changes in Korean.
Approve only if the story aligns with business intent and acceptance criteria.
"""


def dev_prompt(story_key: str, retry: bool) -> str:
    mode = "Fix the implementation using the latest gate logs and QA findings." if retry else "Implement the approved story."
    return common_preamble("dev", story_key) + f"""
Role objective:
- {mode}

Rules:
- Implement only what is required by the active story.
- Read `.bmadx/state/last-gate-dev.log`, `.bmadx/state/last-gate-code_review.log`, and `.bmadx/state/last-gate-qa_verify.log` if they exist.
- Read `.bmadx/reviews/{story_key}.code-review.md` and `.bmadx/reviews/{story_key}.qa-report.md` if they exist.
- Run only manifest-based commands from `.bmadx/state/runtime-manifest.json`.
- Create or update tests when needed.
- Do not claim future or orchestrator-managed state transitions in the dev note.
- Record only facts that are already true at the end of your role step, and label any snapshots as time-sensitive.
- Write `.bmadx/reviews/{story_key}.dev-note.md` with changed files, commands run, and remaining risks.
"""


def code_review_prompt(story_key: str) -> str:
    return common_preamble("qa", story_key) + f"""
Perform an adversarial code review for story '{story_key}'.
Write `.bmadx/reviews/{story_key}.code-review.md` with this exact header:
Verdict: PASS or Verdict: FAIL

Rules:
- Write the report in Korean.
- If Verdict is FAIL, every finding must include an exact file path and line number.
- Focus on security, logic bugs, regression risks, runtime mismatches, and missing tests.
- Do not run the QA verification command set in this phase.
"""


def qa_verify_prompt(story_key: str) -> str:
    return common_preamble("qa", story_key) + f"""
Perform QA verification for story '{story_key}'.
Rules:
- Read `.bmadx/reviews/{story_key}.dev-note.md` and `.bmadx/reviews/{story_key}.code-review.md`.
- Run real verification commands using `.bmadx/state/runtime-manifest.json`.
- Write `.bmadx/reviews/{story_key}.qa-report.md` with this exact header:
Verdict: PASS or Verdict: FAIL
- Then include risks, failing commands, repro steps, and actual command output summaries in Korean.
"""


def retrospective_prompt(retro_key: str) -> str:
    return common_preamble("sm", retro_key) + f"""
Run a concise retrospective for '{retro_key}' based on completed story history.
Write `.bmadx/reviews/{retro_key}.md` with actions and lessons learned.
"""


def read_gate_log(name: str) -> str:
    path = STATE / f"last-gate-{name}.log"
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    return text[-4000:]


def gate(name: str, story_key: str) -> bool:
    cmd = {
        "story": [*bash_prefix(), "scripts/gates/story_review_gate.sh", story_key],
        "dev": [*bash_prefix(), "scripts/gates/dev_gate.sh", story_key],
        "code_review": [*bash_prefix(), "scripts/gates/code_review_gate.sh", story_key],
        "qa_verify": [*bash_prefix(), "scripts/gates/qa_gate.sh", story_key],
    }[name]
    rc, out = run_local(cmd)
    print(out)
    return rc == 0


def set_planner_state(action: dict[str, Any]) -> None:
    write_json(STATE / "planner.json", action)


def resolve_execution_action(action: dict[str, Any]) -> dict[str, Any]:
    story_key = action.get("story_key")
    current = current_phase_state()
    if story_key and current.get("story_key") == story_key and current.get("phase_status") == "blocked":
        return {
            **action,
            "phase": "blocked",
            "reason": current.get("notes") or current.get("next_action") or action.get("reason"),
        }

    phase = action.get("phase")
    resumable = {
        "story": {"create-story", "validate-story", "revise-story"},
        "dev": {"dev-story"},
        "qa": {"code-review", "qa-verify"},
    }
    defaults = {
        "story": "create-story",
        "dev": "dev-story",
        "qa": "code-review",
    }

    if phase in resumable and story_key:
        if current.get("story_key") == story_key and current.get("phase") in resumable[phase]:
            return {**action, "phase": current.get("phase")}
        return {**action, "phase": defaults[phase]}
    return action


def run_create_story_phase(story_key: str) -> None:
    attempt = phase_attempt("story_validation", story_key)
    set_phase_state(story_key, "create-story", "in-progress", attempt, "Creating story artifact.", "Run story validation.")
    rc, out = codex_exec("sm", sm_story_prompt(story_key, revise=False))
    print(out)
    if rc != 0:
        append_phase_history(story_key, "create-story", "exec-error", out[-4000:])
        set_phase_state(story_key, "create-story", "failed", attempt, "Codex failed during create-story.", "Inspect .bmadx/state/last-codex-sm.raw.log.")
        raise SystemExit(rc)
    append_phase_history(story_key, "create-story", "passed", "Story file created or updated.")
    set_phase_state(story_key, "validate-story", "pending", attempt, "Story ready for PM/PO validation.", "Run validation reviews.")


def run_validate_story_phase(story_key: str) -> None:
    attempt = phase_attempt("story_validation", story_key)
    set_phase_state(story_key, "validate-story", "in-progress", attempt, "Running PM/PO validation.", "Collect PM/PO reviews.")
    for role, prompt in (("pm", pm_prompt(story_key)), ("po", po_prompt(story_key))):
        rc, out = codex_exec(role, prompt)
        print(out)
        if rc != 0:
            append_phase_history(story_key, "validate-story", "exec-error", out[-4000:])
            set_phase_state(story_key, "validate-story", "failed", attempt, f"Codex failed during {role} review.", "Inspect raw codex logs.")
            raise SystemExit(rc)

    if gate("story", story_key):
        append_phase_history(story_key, "validate-story", "passed", "Story gate passed and status moved to ready-for-dev.")
        reset_attempt("story_validation", story_key)
        set_phase_state(story_key, "validate-story", "completed", attempt, "Story approved and ready for development.", "Proceed to dev-story.")
        return

    failure_count = bump_attempt("story_validation", story_key)
    note = read_gate_log("story") or "Story validation failed."
    append_phase_history(story_key, "validate-story", "failed", note)
    if failure_count >= STORY_VALIDATION_MAX_ATTEMPTS:
        set_phase_state(
            story_key,
            "validate-story",
            "blocked",
            failure_count,
            f"Story validation exceeded retry limit.\n\n{note}",
            "Manual intervention required before continuing.",
        )
        return
    set_phase_state(
        story_key,
        "revise-story",
        "pending",
        failure_count + 1,
        f"Validation failed and requires story revision.\n\n{note}",
        "Revise the story with PM/PO feedback.",
    )


def run_revise_story_phase(story_key: str) -> None:
    attempt = phase_attempt("story_validation", story_key)
    set_phase_state(story_key, "revise-story", "in-progress", attempt, "Revising story with PM/PO feedback.", "Produce an updated story file.")
    rc, out = codex_exec("sm", sm_story_prompt(story_key, revise=True))
    print(out)
    if rc != 0:
        append_phase_history(story_key, "revise-story", "exec-error", out[-4000:])
        set_phase_state(story_key, "revise-story", "failed", attempt, "Codex failed during revise-story.", "Inspect .bmadx/state/last-codex-sm.raw.log.")
        raise SystemExit(rc)
    append_phase_history(story_key, "revise-story", "passed", "Story revised for another validation pass.")
    set_phase_state(story_key, "validate-story", "pending", attempt, "Story revision complete.", "Run PM/PO validation again.")


def run_dev_story_phase(story_key: str) -> None:
    attempt = phase_attempt("dev_cycle", story_key)
    write_status(ROOT, story_key, "in-progress")
    set_phase_state(story_key, "dev-story", "in-progress", attempt, "Implementing the active story.", "Run dev gate afterwards.")
    rc, out = codex_exec("dev", dev_prompt(story_key, retry=attempt_counter("dev_cycle", story_key) > 0))
    print(out)
    if rc != 0:
        append_phase_history(story_key, "dev-story", "exec-error", out[-4000:])
        set_phase_state(story_key, "dev-story", "failed", attempt, "Codex failed during dev-story.", "Inspect .bmadx/state/last-codex-dev.raw.log.")
        raise SystemExit(rc)

    if gate("dev", story_key):
        write_status(ROOT, story_key, "review")
        append_phase_history(story_key, "dev-story", "passed", "Dev gate passed and story moved to review.")
        set_phase_state(story_key, "code-review", "pending", attempt, "Implementation passed dev gate.", "Run adversarial code review.")
        return

    failure_count = bump_attempt("dev_cycle", story_key)
    note = read_gate_log("dev") or "Dev gate failed."
    append_phase_history(story_key, "dev-story", "failed", note)
    if failure_count >= DEV_CYCLE_MAX_ATTEMPTS:
        set_phase_state(
            story_key,
            "dev-story",
            "blocked",
            failure_count,
            f"Development exceeded retry limit.\n\n{note}",
            "Manual intervention required before continuing.",
        )
        return
    set_phase_state(
        story_key,
        "dev-story",
        "failed",
        failure_count + 1,
        f"Dev gate failed and needs another implementation pass.\n\n{note}",
        "Retry implementation using the latest gate logs.",
    )


def run_code_review_phase(story_key: str) -> None:
    attempt = phase_attempt("dev_cycle", story_key)
    set_phase_state(story_key, "code-review", "in-progress", attempt, "Running adversarial code review.", "Write a PASS/FAIL code review report.")
    rc, out = codex_exec("qa", code_review_prompt(story_key))
    print(out)
    if rc != 0:
        append_phase_history(story_key, "code-review", "exec-error", out[-4000:])
        set_phase_state(story_key, "code-review", "failed", attempt, "Codex failed during code review.", "Inspect .bmadx/state/last-codex-qa.raw.log.")
        raise SystemExit(rc)

    if gate("code_review", story_key):
        append_phase_history(story_key, "code-review", "passed", "Code review passed.")
        set_phase_state(story_key, "qa-verify", "pending", attempt, "Code review passed.", "Run QA verification.")
        return

    failure_count = bump_attempt("dev_cycle", story_key)
    note = read_gate_log("code_review") or "Code review failed."
    append_phase_history(story_key, "code-review", "failed", note)
    write_status(ROOT, story_key, "in-progress")
    if failure_count >= DEV_CYCLE_MAX_ATTEMPTS:
        set_phase_state(
            story_key,
            "code-review",
            "blocked",
            failure_count,
            f"Code review exceeded retry limit.\n\n{note}",
            "Manual intervention required before continuing.",
        )
        return
    set_phase_state(
        story_key,
        "dev-story",
        "failed",
        failure_count + 1,
        f"Code review found issues that require another dev pass.\n\n{note}",
        "Fix code review findings and rerun dev-story.",
    )


def run_qa_verify_phase(story_key: str) -> None:
    attempt = phase_attempt("dev_cycle", story_key)
    set_phase_state(story_key, "qa-verify", "in-progress", attempt, "Running QA verification commands.", "Produce a PASS/FAIL QA report and run the QA gate.")
    rc, out = codex_exec("qa", qa_verify_prompt(story_key))
    print(out)
    if rc != 0:
        append_phase_history(story_key, "qa-verify", "exec-error", out[-4000:])
        set_phase_state(story_key, "qa-verify", "failed", attempt, "Codex failed during QA verification.", "Inspect .bmadx/state/last-codex-qa.raw.log.")
        raise SystemExit(rc)

    if gate("qa_verify", story_key):
        append_phase_history(story_key, "qa-verify", "passed", "QA verification passed and story moved to done.")
        reset_attempt("dev_cycle", story_key)
        set_phase_state(story_key, "qa-verify", "completed", attempt, "Story completed.", "Proceed to the next available story.")
        return

    failure_count = bump_attempt("dev_cycle", story_key)
    note = read_gate_log("qa_verify") or "QA verification failed."
    append_phase_history(story_key, "qa-verify", "failed", note)
    write_status(ROOT, story_key, "in-progress")
    if failure_count >= DEV_CYCLE_MAX_ATTEMPTS:
        set_phase_state(
            story_key,
            "qa-verify",
            "blocked",
            failure_count,
            f"QA verification exceeded retry limit.\n\n{note}",
            "Manual intervention required before continuing.",
        )
        return
    set_phase_state(
        story_key,
        "dev-story",
        "failed",
        failure_count + 1,
        f"QA verification failed and requires another dev pass.\n\n{note}",
        "Fix QA findings and rerun dev-story.",
    )


def run_retrospective_phase(retro_key: str) -> None:
    set_phase_state(retro_key, "retrospective", "in-progress", 1, "Running epic retrospective.", "Write the retrospective report.")
    rc, out = codex_exec("sm", retrospective_prompt(retro_key))
    print(out)
    if rc != 0:
        append_phase_history(retro_key, "retrospective", "exec-error", out[-4000:])
        set_phase_state(retro_key, "retrospective", "failed", 1, "Codex failed during retrospective.", "Inspect .bmadx/state/last-codex-sm.raw.log.")
        raise SystemExit(rc)
    from sprint_status import write_status as _write_status

    _write_status(ROOT, retro_key, "completed")
    append_phase_history(retro_key, "retrospective", "passed", "Retrospective completed.")
    set_phase_state(retro_key, "retrospective", "completed", 1, "Retrospective completed.", "Proceed to the next epic.")


def parse_args(argv: list[str]) -> dict[str, Any]:
    forced_story = None
    max_cycles = 12
    i = 1
    while i < len(argv):
        token = argv[i]
        if token == "--story" and i + 1 < len(argv):
            forced_story = argv[i + 1]
            i += 2
        elif token == "--max-cycles" and i + 1 < len(argv):
            max_cycles = int(argv[i + 1])
            i += 2
        else:
            i += 1
    return {"forced_story": forced_story, "max_cycles": max_cycles}


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    ensure_state()
    if args["max_cycles"] <= 0:
        print("No cycles requested.")
        return 0

    for _ in range(args["max_cycles"]):
        spath, data = load_sprint_status(ROOT)
        if spath is None:
            print("sprint-status.yaml not found")
            return 1

        action = resolve_execution_action(choose_next_action(ROOT, data, forced_story=args["forced_story"]))
        set_planner_state(action)
        print(json.dumps(action, ensure_ascii=False, indent=2))

        phase = action.get("phase")
        if phase == "done":
            set_phase_state(None, None, "idle", 0, "No actionable stories remain.", "")
            print("Done: no actionable stories remain.")
            return 0
        if phase == "blocked":
            print(action.get("reason") or "Execution is blocked and requires manual intervention.")
            return 1
        if phase == "create-story":
            run_create_story_phase(action["story_key"])
            continue
        if phase == "validate-story":
            run_validate_story_phase(action["story_key"])
            continue
        if phase == "revise-story":
            run_revise_story_phase(action["story_key"])
            continue
        if phase == "dev-story":
            run_dev_story_phase(action["story_key"])
            continue
        if phase == "code-review":
            run_code_review_phase(action["story_key"])
            continue
        if phase == "qa-verify":
            run_qa_verify_phase(action["story_key"])
            continue
        if phase == "retrospective":
            run_retrospective_phase(action["retro_key"])
            continue

        print(f"Unsupported phase: {phase}")
        return 1

    print("Stopped after reaching max cycles.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
