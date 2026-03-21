#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

CANDIDATE_PATHS = [
    ".bmad-ephemeral/sprint-status.yaml",
    "_bmad-output/implementation-artifacts/sprint-status.yaml",
    "docs/sprint-status.yaml",
    "sprint-status.yaml",
]

STORY_DONE = {"done"}
STORY_REVIEW = {"review"}
STORY_DEV = {"ready-for-dev", "drafted", "in-progress"}
STORY_CREATE = {"backlog"}

TOP_LEVEL_KEYS = {"project", "project_key", "tracking_system", "story_location", "development_status"}


def locate_sprint_status(root: Path) -> Path | None:
    for rel in CANDIDATE_PATHS:
        p = root / rel
        if p.exists():
            return p
    for base in [root / ".bmad-ephemeral", root / "_bmad-output", root / "docs", root]:
        if base.exists():
            for p in base.rglob("sprint-status.yaml"):
                return p
    return None


def _normalize_scalar(value: str) -> str:
    return value.strip().strip("\"'")


def normalize_status(value: str) -> str:
    raw = _normalize_scalar(value).lower().replace("_", "-").replace(" ", "-")
    aliases = {
        "ready-for-review": "review",
        "ready-review": "review",
        "ready": "ready-for-dev",
        "started": "in-progress",
        "complete": "done",
        "completed": "completed",
    }
    return aliases.get(raw, raw)


def _load_with_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return {}
    return data


def _load_manual(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"development_status": {}}
    current = None
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.rstrip()
        if indent == 0 and ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            if key == "development_status":
                current = "development_status"
                if value.strip():
                    result[key] = {}
            elif key in TOP_LEVEL_KEYS:
                result[key] = _normalize_scalar(value)
                current = None
            else:
                current = None
        elif current == "development_status" and ":" in line:
            key, value = line.strip().split(":", 1)
            result["development_status"][key.strip()] = _normalize_scalar(value)
    return result


def load_sprint_status(root: Path) -> tuple[Path | None, dict[str, Any]]:
    path = locate_sprint_status(root)
    if not path:
        return None, {}
    data = _load_with_yaml(path) or _load_manual(path)
    data.setdefault("development_status", {})
    dev = data.get("development_status") or {}
    norm_dev: dict[str, str] = {}
    for k, v in dev.items():
        norm_dev[str(k)] = normalize_status(str(v))
    data["development_status"] = norm_dev
    return path, data


def save_sprint_status(path: Path, data: dict[str, Any]) -> None:
    data = dict(data)
    data["development_status"] = {str(k): normalize_status(str(v)) for k, v in (data.get("development_status") or {}).items()}
    if yaml is not None:
        path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
        return
    lines: list[str] = []
    for key in ["project", "project_key", "tracking_system", "story_location"]:
        if key in data and data[key] not in (None, ""):
            lines.append(f"{key}: {data[key]}")
    lines.append("development_status:")
    for k, v in data.get("development_status", {}).items():
        lines.append(f"  {k}: {v}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_status(root: Path, story_or_key: str, status: str) -> Path:
    path, data = load_sprint_status(root)
    if path is None:
        raise FileNotFoundError("sprint-status.yaml not found")
    dev = data.setdefault("development_status", {})
    dev[story_or_key] = normalize_status(status)
    save_sprint_status(path, data)
    return path


def classify_key(key: str) -> str:
    k = key.lower()
    if re.fullmatch(r"epic-\d+", k):
        return "epic"
    if "retrospective" in k:
        return "retrospective"
    return "story"


def extract_epic_number(key: str) -> str | None:
    patterns = [
        r"^epic-(\d+)$",
        r"^epic-(\d+)-",
        r"^(\d+)[.-](\d+)",
        r"story-(\d+)[.-](\d+)",
        r"story-(\d+)-(\d+)",
    ]
    for pat in patterns:
        m = re.search(pat, key.lower())
        if m:
            return m.group(1)
    return None


def find_story_keys(data: dict[str, Any]) -> list[str]:
    return [k for k in (data.get("development_status") or {}).keys() if classify_key(k) == "story"]


def find_epic_keys(data: dict[str, Any]) -> list[str]:
    return [k for k in (data.get("development_status") or {}).keys() if classify_key(k) == "epic"]


def find_retro_keys(data: dict[str, Any]) -> list[str]:
    return [k for k in (data.get("development_status") or {}).keys() if classify_key(k) == "retrospective"]


def story_location_path(root: Path, data: dict[str, Any]) -> Path:
    rel = str(data.get("story_location") or "_bmad-output/planning-artifacts/stories")
    p = Path(rel)
    return p if p.is_absolute() else (root / p)


def possible_story_paths(root: Path, data: dict[str, Any], story_key: str) -> list[Path]:
    story_dir = story_location_path(root, data)
    candidates: list[Path] = []
    raw = story_key.strip()
    slugs = {raw, raw.replace(".", "-"), raw.replace(" ", "-"), raw.lower()}
    # Common BMAD filenames
    for slug in list(slugs):
        slugs.add(f"{slug}-story")
        slugs.add(f"story-{slug}")
    # Numeric story conventions
    m = re.match(r"^(\d+)[.-](\d+)$", raw)
    if m:
        e, s = m.groups()
        slugs.update({f"{e}.{s}-story", f"{e}-{s}-story", f"story-{e}-{s}", f"epic-{e}-story-{s}"})
    for slug in slugs:
        candidates.append(story_dir / f"{slug}.md")
    if story_dir.exists():
        for p in story_dir.rglob("*.md"):
            name = p.stem.lower()
            if raw.lower() in name or raw.replace(".", "-").lower() in name:
                candidates.append(p)
    seen = set()
    uniq = []
    for p in candidates:
        if str(p) not in seen:
            uniq.append(p)
            seen.add(str(p))
    return uniq


def resolve_story_file(root: Path, data: dict[str, Any], story_key: str) -> Path | None:
    for p in possible_story_paths(root, data, story_key):
        if p.exists():
            return p
    return None


def ordered_story_items(data: dict[str, Any]) -> list[tuple[str, str]]:
    dev = data.get("development_status") or {}
    return [(k, v) for k, v in dev.items() if classify_key(k) == "story"]


def all_stories_done_for_epic(data: dict[str, Any], epic_number: str) -> bool:
    found = False
    for key, status in ordered_story_items(data):
        if extract_epic_number(key) == epic_number:
            found = True
            if normalize_status(status) != "done":
                return False
    return found


def mark_epic_done_if_ready(root: Path, data: dict[str, Any], epic_number: str) -> None:
    if not all_stories_done_for_epic(data, epic_number):
        return
    epic_key = f"epic-{epic_number}"
    retro_key = f"epic-{epic_number}-retrospective"
    path, latest = load_sprint_status(root)
    if path is None:
        return
    latest.setdefault("development_status", {})
    latest["development_status"][epic_key] = "done"
    if retro_key in latest["development_status"] and latest["development_status"][retro_key] not in {"completed"}:
        latest["development_status"][retro_key] = latest["development_status"][retro_key] or "optional"
    save_sprint_status(path, latest)


def choose_next_action(root: Path, data: dict[str, Any], forced_story: str | None = None) -> dict[str, Any]:
    dev = data.get("development_status") or {}
    items = ordered_story_items(data)
    if forced_story:
        items = [(k, v) for k, v in items if forced_story in {k, k.replace('-', '.'), k.replace('.', '-')}]

    # Priority 1: review
    for key, status in items:
        if normalize_status(status) == "review":
            return {"phase": "qa", "story_key": key, "status": status, "reason": "story waiting for review"}

    # Priority 2: active dev
    for key, status in items:
        if normalize_status(status) == "in-progress":
            return {"phase": "dev", "story_key": key, "status": status, "reason": "story already in progress"}

    # Priority 3: ready for dev / drafted
    for key, status in items:
        n = normalize_status(status)
        if n in {"ready-for-dev", "drafted"}:
            return {"phase": "dev", "story_key": key, "status": n, "reason": "story ready for implementation"}

    # Priority 4: backlog -> create story
    for key, status in items:
        if normalize_status(status) == "backlog":
            return {"phase": "story", "story_key": key, "status": status, "reason": "story still in backlog"}

    # Optional retrospective when epic done and retro still not completed
    for key, status in dev.items():
        if classify_key(key) == "retrospective" and normalize_status(status) == "optional":
            return {"phase": "retrospective", "retro_key": key, "status": status, "reason": "epic complete, retrospective optional"}

    return {"phase": "done", "reason": "no actionable story found"}
