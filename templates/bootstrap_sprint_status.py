#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

from sprint_status import load_sprint_status, save_sprint_status

ROOT = Path(__file__).resolve().parents[2]

STORY_PATTERNS = [
    re.compile(r"\b(\d+[.-]\d+)\b"),
    re.compile(r"\bstory[- ]?(\d+[.-]\d+)\b", re.I),
    re.compile(r"\bepic[- ]?(\d+)[- ]+story[- ]?(\d+)\b", re.I),
]


def story_key_sort(key: str) -> tuple[int, int, str]:
    m = re.match(r"^(\d+)[.-](\d+)$", key)
    if m:
        return (int(m.group(1)), int(m.group(2)), key)
    m = re.search(r"(\d+)[.-](\d+)", key)
    if m:
        return (int(m.group(1)), int(m.group(2)), key)
    return (999999, 999999, key)


def normalize_story_key(raw: str) -> str:
    raw = raw.strip().lower().replace('_', '-').replace(' ', '-')
    raw = raw.replace('story-', '')
    m = re.match(r"^(\d+)[.-](\d+)$", raw)
    if m:
        return f"{m.group(1)}.{m.group(2)}"
    m = re.search(r"(\d+)[.-](\d+)", raw)
    if m:
        return f"{m.group(1)}.{m.group(2)}"
    return raw


def extract_story_keys_from_text(text: str) -> set[str]:
    found: set[str] = set()
    for pat in STORY_PATTERNS:
        for m in pat.finditer(text):
            if m.lastindex == 2:
                found.add(f"{m.group(1)}.{m.group(2)}")
            else:
                found.add(normalize_story_key(m.group(1)))
    return {k for k in found if re.match(r"^\d+\.\d+$", k)}


def extract_story_keys_from_files(root: Path) -> list[str]:
    candidates: set[str] = set()
    search_dirs = [
        root / '_bmad-output' / 'planning-artifacts',
        root / '_bmad-output' / 'implementation-artifacts',
    ]
    for base in search_dirs:
        if not base.exists():
            continue
        for p in base.rglob('*.md'):
            if p.name == 'sprint-status.yaml':
                continue
            stem_keys = extract_story_keys_from_text(p.stem)
            candidates.update(stem_keys)
            try:
                text = p.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                text = ''
            candidates.update(extract_story_keys_from_text(text[:12000]))
    return sorted(candidates, key=story_key_sort)


def project_name(root: Path) -> str:
    return root.name


def main() -> int:
    path, data = load_sprint_status(ROOT)
    if path is not None:
        print(f'sprint status already exists: {path}')
        return 0

    story_keys = extract_story_keys_from_files(ROOT)
    if not story_keys:
        print('no stories found in planning artifacts; sprint-status not created')
        return 0

    impl_dir = ROOT / '_bmad-output' / 'implementation-artifacts'
    impl_dir.mkdir(parents=True, exist_ok=True)
    path = impl_dir / 'sprint-status.yaml'

    dev_status: dict[str, str] = {}
    epic_numbers = sorted({k.split('.', 1)[0] for k in story_keys}, key=lambda x: int(x))
    for epic_no in epic_numbers:
        dev_status[f'epic-{epic_no}'] = 'backlog'
    for key in story_keys:
        dev_status[key] = 'backlog'
    for epic_no in epic_numbers:
        dev_status[f'epic-{epic_no}-retrospective'] = 'optional'

    data = {
        'project': project_name(ROOT),
        'project_key': project_name(ROOT).lower().replace(' ', '-'),
        'tracking_system': 'file-based',
        'story_location': '_bmad-output/implementation-artifacts',
        'development_status': dev_status,
    }
    save_sprint_status(path, data)
    print(f'bootstrapped sprint status: {path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
