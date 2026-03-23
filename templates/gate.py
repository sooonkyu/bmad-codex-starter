#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from sprint_status import load_sprint_status, resolve_story_file, write_status, mark_epic_done_if_ready, extract_epic_number

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".bmadx" / "state"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def write_log(name: str, text: str) -> None:
    (STATE / f"last-gate-{name}.log").write_text(text, encoding="utf-8")


def normalize_commands(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item]
    return []


def run_cmd(cmd: str) -> tuple[int, str]:
    proc = subprocess.run(["bash", "-lc", cmd], cwd=ROOT, capture_output=True, text=True)
    output = f"$ {cmd}\n\n[exit={proc.returncode}]\n{proc.stdout}\n{proc.stderr}"
    return proc.returncode, output


def approved_review(path: Path) -> bool:
    if not path.exists():
        return False
    return "approved: yes" in read_text(path).lower()


def report_verdict(path: Path) -> str | None:
    if not path.exists():
        return None
    text = read_text(path).lower()
    if "verdict: pass" in text:
        return "pass"
    if "verdict: fail" in text:
        return "fail"
    return None


def story_file_quality_failures(path: Path) -> list[str]:
    text = read_text(path)
    lowered = text.lower()
    failures: list[str] = []
    required_sections = [
        "## story",
        "## acceptance criteria",
        "## tasks",
        "## dev notes",
        "## dev agent record",
    ]
    for section in required_sections:
        if section not in lowered:
            failures.append(f"missing required story section: {section}")
    if "- [ ]" not in text and "- [x]" not in lowered:
        failures.append("story file does not contain task checkboxes")
    return failures


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
    failures: list[str] = []

    if story_file is None:
        failures.append("story file not found in story_location")
    else:
        failures.extend(story_file_quality_failures(story_file))
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
    install = normalize_commands(manifest.get("commands", {}).get("install"))
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
    logs: list[str] = []
    all_ok = True

    for cmd in normalize_commands(bootstrap.get("services", [])):
        rc, out = run_cmd(cmd)
        logs.append(out)
        if rc != 0:
            all_ok = False
            break

    if all_ok:
        for cmd in normalize_commands(bootstrap.get("migrations", [])):
            rc, out = run_cmd(cmd)
            logs.append(out)
            if rc != 0:
                all_ok = False
                break

    if all_ok:
        for key in keys:
            for cmd in normalize_commands(commands.get(key, [])):
                rc, out = run_cmd(cmd)
                logs.append(out)
                if rc != 0:
                    all_ok = False
                    break
            if not all_ok:
                break

    text = "\n\n".join(logs) if logs else "no commands configured"
    write_log(group_name, text)
    print(text)
    return 0 if all_ok else 1


def dev_gate(story_key: str) -> int:
    return run_manifest_commands("dev", ["lint", "typecheck", "test_unit", "build"])


def code_review_gate(story_key: str) -> int:
    review_path = ROOT / ".bmadx" / "reviews" / f"{story_key}.code-review.md"
    verdict = report_verdict(review_path)
    if verdict == "pass":
        msg = f"code review gate passed\nreview_file={review_path}"
        write_log("code_review", msg)
        print(msg)
        return 0

    if verdict == "fail":
        msg = f"code review gate failed\nreview_file={review_path}\nreason=review verdict FAIL"
    else:
        msg = f"code review gate failed\nreview_file={review_path}\nreason=missing or invalid verdict header"
    write_log("code_review", msg)
    print(msg)
    return 1


def qa_verify_gate(story_key: str) -> int:
    report_path = ROOT / ".bmadx" / "reviews" / f"{story_key}.qa-report.md"
    verdict = report_verdict(report_path)
    if verdict != "pass":
        reason = "review verdict FAIL" if verdict == "fail" else "missing or invalid verdict header"
        msg = f"qa verify gate failed\nreport_file={report_path}\nreason={reason}"
        write_log("qa_verify", msg)
        print(msg)
        return 1

    rc = run_manifest_commands("qa_verify", ["test_integration", "test_e2e", "build"])
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
        print("usage: gate.py [env|story|dev|code_review|qa_verify|qa] [story_key]")
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
    if mode == "code_review":
        if len(argv) < 3:
            print("story key required")
            return 2
        return code_review_gate(argv[2])
    if mode in {"qa_verify", "qa"}:
        if len(argv) < 3:
            print("story key required")
            return 2
        return qa_verify_gate(argv[2])
    print(f"unknown mode: {mode}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
