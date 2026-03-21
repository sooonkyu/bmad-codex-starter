#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from sprint_status import load_sprint_status, resolve_story_file, write_status, mark_epic_done_if_ready, extract_epic_number

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".bmadx" / "state"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_log(name: str, text: str) -> None:
    (STATE / f"last-gate-{name}.log").write_text(text, encoding="utf-8")


def run_cmd(cmd: str) -> tuple[int, str]:
    proc = subprocess.run(["bash", "-lc", cmd], cwd=ROOT, capture_output=True, text=True)
    output = f"$ {cmd}\n\n[exit={proc.returncode}]\n{proc.stdout}\n{proc.stderr}"
    return proc.returncode, output


def approved_review(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="ignore").lower()
    return "approved: yes" in text


def story_gate(story_key: str) -> int:
    spath, data = load_sprint_status(ROOT)
    if spath is None:
        msg = "sprint-status.yaml missing"
        write_log("story", msg)
        print(msg)
        return 1

    story_file = resolve_story_file(ROOT, data, story_key)
    pm_review = ROOT / ".bmadx" / "reviews" / f"{story_key}.pm-review.md"
    po_review = ROOT / ".bmadx" / "reviews" / f"{story_key}.po-review.md"
    failures = []
    if story_file is None:
        failures.append("story file not found in story_location")
    if not approved_review(pm_review):
        failures.append("PM review not approved")
    if not approved_review(po_review):
        failures.append("PO review not approved")

    if failures:
        msg = "story gate failed\n- " + "\n- ".join(failures)
        write_log("story", msg)
        print(msg)
        return 1

    write_status(ROOT, story_key, "ready-for-dev")
    msg = f"story gate passed\nstory_file={story_file}\nstatus updated to ready-for-dev"
    write_log("story", msg)
    print(msg)
    return 0


def env_gate() -> int:
    manifest_path = ROOT / ".bmadx" / "state" / "runtime-manifest.json"
    if not manifest_path.exists():
        msg = "runtime-manifest.json missing"
        write_log("env", msg)
        print(msg)
        return 1

    manifest = read_json(manifest_path)
    primary = manifest.get("runtime", {}).get("primary")
    install = manifest.get("commands", {}).get("install")
    if not primary or primary == "unknown" or not install:
        msg = f"manifest incomplete: primary={primary}, install={install!r}"
        write_log("env", msg)
        print(msg)
        return 1

    msg = "env gate passed"
    write_log("env", msg)
    print(msg)
    return 0


def run_manifest_commands(group_name: str, keys: list[str]) -> int:
    manifest = read_json(ROOT / ".bmadx" / "state" / "runtime-manifest.json")
    commands = manifest.get("commands", {})
    bootstrap = manifest.get("bootstrap", {})
    logs = []
    all_ok = True

    for cmd in bootstrap.get("services", []):
        if not cmd:
            continue
        rc, out = run_cmd(cmd)
        logs.append(out)
        if rc != 0:
            all_ok = False
            break

    if all_ok and bootstrap.get("migrations"):
        rc, out = run_cmd(bootstrap["migrations"])
        logs.append(out)
        if rc != 0:
            all_ok = False

    for key in keys:
        cmd = commands.get(key, "")
        if not cmd:
            continue
        rc, out = run_cmd(cmd)
        logs.append(out)
        if rc != 0:
            all_ok = False
            break

    text = "\n\n".join(logs) if logs else "no commands configured"
    write_log(group_name, text)
    print(text)
    return 0 if all_ok else 1


def dev_gate(story_key: str) -> int:
    return run_manifest_commands("dev", ["lint", "typecheck", "test_unit", "build"])


def qa_gate(story_key: str) -> int:
    rc = run_manifest_commands("qa", ["test_integration", "test_e2e", "build"])
    if rc != 0:
        return rc
    write_status(ROOT, story_key, "done")
    spath, data = load_sprint_status(ROOT)
    if spath is not None:
        epic_no = extract_epic_number(story_key)
        if epic_no:
            mark_epic_done_if_ready(ROOT, data, epic_no)
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: gate.py [env|story|dev|qa] [story_key]")
        return 2
    mode = argv[1]
    if mode == "env":
        return env_gate()
    if mode == "story":
        if len(argv) < 3:
            print("story key required")
            return 2
        return story_gate(argv[2])
    if mode == "dev":
        if len(argv) < 3:
            print("story key required")
            return 2
        return dev_gate(argv[2])
    if mode == "qa":
        if len(argv) < 3:
            print("story key required")
            return 2
        return qa_gate(argv[2])
    print(f"unknown mode: {mode}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
