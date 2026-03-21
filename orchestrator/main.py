#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def find_project_root() -> Path:
    env_root = os.environ.get('BMADX_PROJECT_ROOT')
    if env_root:
        return Path(env_root).resolve()
    candidates = [Path.cwd(), Path(__file__).resolve()]
    for start in candidates:
        p = start if start.is_dir() else start.parent
        for base in [p, *p.parents]:
            marker = base / '.bmadx' / 'state' / 'install-context.json'
            if marker.exists():
                try:
                    data = json.loads(marker.read_text(encoding='utf-8'))
                    proj = data.get('project_root')
                    if proj:
                        return Path(proj).resolve()
                except Exception:
                    pass
            if (base / 'tools' / 'bmad-codex').exists() and (base / '.bmadx').exists():
                return base.resolve()
    return Path(__file__).resolve().parents[3]


ROOT = find_project_root()
STATE = ROOT / '.bmadx' / 'state'
SESSIONS = STATE / 'sessions.json'
REVIEWS = ROOT / '.bmadx' / 'reviews'

sys.path.insert(0, str(ROOT / 'scripts' / 'bmadx'))
from sprint_status import load_sprint_status, locate_sprint_status, choose_next_action, write_status, resolve_story_file, story_location_path


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')


def host_env() -> dict[str, Any]:
    return read_json(STATE / 'host-env.json', {})


def python_cmd() -> list[str]:
    he = host_env()
    cmd = he.get('execution', {}).get('python_cmd')
    if isinstance(cmd, list) and cmd:
        return cmd
    return [sys.executable or 'python3']


def bash_prefix() -> list[str]:
    he = host_env()
    cmd = he.get('execution', {}).get('bash_cmd')
    if isinstance(cmd, list) and cmd:
        return cmd
    return ['bash']


def codex_cmd() -> list[str]:
    override = os.environ.get('BMADX_CODEX', '').strip()
    if override:
        return shlex.split(override)
    he = host_env()
    cmd = he.get('execution', {}).get('codex_cmd')
    if isinstance(cmd, list) and cmd:
        return cmd
    return ['codex']


def run_local(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    out = (proc.stdout or '') + ('\n' + proc.stderr if proc.stderr else '')
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
    must([*python_cmd(), 'scripts/bmadx/index_bmad.py'])
    must([*bash_prefix(), 'scripts/gates/discover_env_gate.sh'])
    must([*python_cmd(), 'scripts/bmadx/bootstrap_sprint_status.py'])
    sprint = locate_sprint_status(ROOT)
    (STATE / 'sprint-status.path').write_text(str(sprint) if sprint else '', encoding='utf-8')


def load_sessions() -> dict[str, str]:
    return read_json(SESSIONS, {})


def save_sessions(data: dict[str, str]) -> None:
    write_json(SESSIONS, data)


def codex_exec(role: str, prompt: str) -> tuple[int, str]:
    base = codex_cmd()
    if shutil.which(base[0]) is None and os.path.basename(base[0]).lower() != 'wsl.exe':
        return 127, f'codex CLI not found: {base[0]}'
    sessions = load_sessions()
    session_id = sessions.get(role)
    if session_id:
        cmd = [*base, 'exec', 'resume', session_id, '--json', '--full-auto', '--sandbox', 'workspace-write', '--cd', str(ROOT), prompt]
    else:
        cmd = [*base, 'exec', '--json', '--full-auto', '--sandbox', 'workspace-write', '--cd', str(ROOT), prompt]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    raw = (proc.stdout or '') + ('\n' + proc.stderr if proc.stderr else '')
    (STATE / f'last-codex-{role}.raw.log').write_text(raw, encoding='utf-8')

    new_thread_id = None
    final_texts: list[str] = []
    for line in (proc.stdout or '').splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get('type') == 'thread.started':
            new_thread_id = obj.get('thread_id')
        item = obj.get('item') or {}
        if item.get('type') == 'agent_message':
            txt = item.get('text')
            if txt:
                final_texts.append(txt)
    if new_thread_id:
        sessions[role] = new_thread_id
        save_sessions(sessions)
    return proc.returncode, '\n\n'.join(final_texts).strip() or raw.strip()


def role_map() -> dict:
    return read_json(STATE / 'role-map.json', {'agents': {}, 'workflow_roots': []})


def common_preamble(role: str, story_key: str) -> str:
    rm = role_map()
    agent_md = rm.get('agents', {}).get(role)
    workflow_roots = rm.get('workflow_roots', [])
    he = host_env()
    spath, data = load_sprint_status(ROOT)
    story_file = resolve_story_file(ROOT, data, story_key) if spath else None
    story_dir = story_location_path(ROOT, data) if spath else ROOT / '_bmad-output/planning-artifacts/stories'
    return f"""
Repository root: {ROOT}
Host environment: {json.dumps(he, ensure_ascii=False)}
Sprint status file: {spath}
Story location directory: {story_dir}
Current target story key: {story_key}
Existing story file: {story_file}

Mandatory steps:
1. Read AGENTS.override.md
2. Read .bmadx/state/host-env.json
3. Read .bmadx/state/runtime-manifest.json
4. Read .bmadx/state/role-map.json
5. Read .bmadx/state/sprint-status.path and then the sprint-status file itself
6. Load the BMAD agent markdown for role '{role}': {agent_md}
7. If the agent markdown references workflow files, load them.
8. If referenced workflow paths are broken, search neighboring workflow roots under: {workflow_roots}
9. Do real file edits and real command runs. Do not only describe what should happen.
10. Never claim this phase is complete unless the relevant gate can pass.
"""


def sm_story_prompt(story_key: str) -> str:
    return common_preamble('sm', story_key) + f"""
Role objective:
- Create or revise the BMAD story for story key '{story_key}' based on epic context, sprint-status, and planning artifacts.

Instructions:
- Find the story details for '{story_key}' in `_bmad-output/planning-artifacts/epics/` or nearby planning artifacts.
- Create or update the actual BMAD story file under the story_location path from sprint-status.
- Keep the story aligned with BMAD style as closely as possible.
- Do not approve the story yourself.
"""


def pm_prompt(story_key: str) -> str:
    return common_preamble('pm', story_key) + f"""
Review the current story for '{story_key}' as PM.
Write `.bmadx/reviews/{story_key}.pm-review.md` with this exact header:
Approved: YES or Approved: NO
Then include concise reasons and required changes.
Approve only if the story is clear, implementable, and testable.
"""


def po_prompt(story_key: str) -> str:
    return common_preamble('po', story_key) + f"""
Review the current story for '{story_key}' as PO.
Write `.bmadx/reviews/{story_key}.po-review.md` with this exact header:
Approved: YES or Approved: NO
Then include concise reasons and required changes.
Approve only if the story aligns with business intent and acceptance criteria.
"""


def dev_prompt(story_key: str, retry: bool) -> str:
    mode = 'Fix the implementation using the latest gate logs and QA report.' if retry else 'Implement the approved story.'
    return common_preamble('dev', story_key) + f"""
Role objective:
- {mode}

Rules:
- Implement only what is required by the active story.
- Read `.bmadx/state/last-gate-dev.log` and `.bmadx/state/last-gate-qa.log` if they exist.
- Run only manifest-based commands from `.bmadx/state/runtime-manifest.json`.
- Create or update tests when needed.
- Write `.bmadx/reviews/{story_key}.dev-note.md` with changed files, commands run, and remaining risks.
"""


def qa_prompt(story_key: str) -> str:
    return common_preamble('qa', story_key) + f"""
Perform QA verification for story '{story_key}'.
Rules:
- Read `.bmadx/reviews/{story_key}.dev-note.md`.
- Run real verification commands using `.bmadx/state/runtime-manifest.json`.
- Write `.bmadx/reviews/{story_key}.qa-report.md` with this exact header:
Verdict: PASS or Verdict: FAIL
Then include risks, failing commands, repro steps, and minimal fix guidance.
"""


def retrospective_prompt(retro_key: str) -> str:
    return common_preamble('sm', retro_key) + f"""
Run a concise retrospective for '{retro_key}' based on completed story history.
Write `.bmadx/reviews/{retro_key}.md` with actions and lessons learned.
"""


def gate(name: str, story_key: str) -> bool:
    cmd = {
        'story': [*bash_prefix(), 'scripts/gates/story_review_gate.sh', story_key],
        'dev': [*bash_prefix(), 'scripts/gates/dev_gate.sh', story_key],
        'qa': [*bash_prefix(), 'scripts/gates/qa_gate.sh', story_key],
    }[name]
    rc, out = run_local(cmd)
    print(out)
    return rc == 0


def set_planner_state(action: dict[str, Any]) -> None:
    write_json(STATE / 'planner.json', action)


def run_story_cycle(story_key: str) -> bool:
    rc, out = codex_exec('sm', sm_story_prompt(story_key))
    print(out)
    if rc != 0:
        raise SystemExit(rc)
    rc, out = codex_exec('pm', pm_prompt(story_key))
    print(out)
    if rc != 0:
        raise SystemExit(rc)
    rc, out = codex_exec('po', po_prompt(story_key))
    print(out)
    if rc != 0:
        raise SystemExit(rc)
    return gate('story', story_key)


def run_dev_qa_cycle(story_key: str) -> bool:
    write_status(ROOT, story_key, 'in-progress')
    rc, out = codex_exec('dev', dev_prompt(story_key, retry=False))
    print(out)
    if rc != 0:
        raise SystemExit(rc)
    if not gate('dev', story_key):
        return False
    rc, out = codex_exec('qa', qa_prompt(story_key))
    print(out)
    if rc != 0:
        raise SystemExit(rc)
    if gate('qa', story_key):
        return True
    write_status(ROOT, story_key, 'in-progress')
    return False


def parse_args(argv: list[str]) -> dict[str, Any]:
    forced_story = None
    max_cycles = 12
    i = 1
    while i < len(argv):
        token = argv[i]
        if token == '--story' and i + 1 < len(argv):
            forced_story = argv[i + 1]
            i += 2
        elif token == '--max-cycles' and i + 1 < len(argv):
            max_cycles = int(argv[i + 1])
            i += 2
        else:
            i += 1
    return {'forced_story': forced_story, 'max_cycles': max_cycles}


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    ensure_state()
    for _ in range(args['max_cycles']):
        spath, data = load_sprint_status(ROOT)
        if spath is None:
            print('sprint-status.yaml not found')
            return 1
        action = choose_next_action(ROOT, data, forced_story=args['forced_story'])
        set_planner_state(action)
        print(json.dumps(action, ensure_ascii=False, indent=2))
        phase = action.get('phase')
        if phase == 'done':
            print('Done: no actionable stories remain.')
            return 0
        if phase == 'story':
            ok = run_story_cycle(action['story_key'])
            if ok:
                continue
            print('Story review failed -> re-entering SM')
            continue
        if phase == 'dev':
            ok = run_dev_qa_cycle(action['story_key'])
            if ok:
                continue
            print('DEV/QA failed -> re-entering DEV')
            continue
        if phase == 'qa':
            rc, out = codex_exec('qa', qa_prompt(action['story_key']))
            print(out)
            if rc != 0:
                return rc
            if gate('qa', action['story_key']):
                continue
            write_status(ROOT, action['story_key'], 'in-progress')
            print('QA failed -> returning to DEV')
            continue
        if phase == 'retrospective':
            retro_key = action['retro_key']
            rc, out = codex_exec('sm', retrospective_prompt(retro_key))
            print(out)
            if rc != 0:
                return rc
            from sprint_status import write_status as _ws
            _ws(ROOT, retro_key, 'completed')
            continue
        print(f'Unsupported phase: {phase}')
        return 1
    print('Stopped after reaching max cycles.')
    return 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
