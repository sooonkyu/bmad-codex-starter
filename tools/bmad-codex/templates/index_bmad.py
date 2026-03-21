#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BMAD_ROOT = ROOT / "_bmad"
STATE = ROOT / ".bmadx" / "state"
OUT = STATE / "role-map.json"

ROLE_KEYWORDS = {
    "sm": ["scrum master", "story", "sm"],
    "pm": ["product manager", "pm"],
    "po": ["product owner", "po"],
    "dev": ["developer", "engineer", "dev"],
    "qa": ["qa", "quality", "test", "sdet", "quinn", "tea"],
}

def score_file(path: Path, keywords: list[str]) -> int:
    score = 0
    lower_path = str(path).lower()
    try:
        text = path.read_text(encoding="utf-8", errors="ignore").lower()[:6000]
    except Exception:
        text = ""
    for kw in keywords:
        if kw in lower_path:
            score += 3
        if kw in text:
            score += 2
    if "/agents/" in lower_path.replace("\\", "/"):
        score += 5
    return score

def main() -> int:
    STATE.mkdir(parents=True, exist_ok=True)
    result = {"agents": {}, "workflow_roots": []}

    if BMAD_ROOT.exists():
        md_files = list(BMAD_ROOT.rglob("*.md"))
        workflow_dirs = {str(p.relative_to(ROOT)) for p in BMAD_ROOT.rglob("workflows") if p.is_dir()}
        result["workflow_roots"] = sorted(workflow_dirs)

        for role, keywords in ROLE_KEYWORDS.items():
            candidates = sorted(md_files, key=lambda p: score_file(p, keywords), reverse=True)
            best = next((c for c in candidates if score_file(c, keywords) > 0), None)
            result["agents"][role] = str(best.relative_to(ROOT)) if best else None
    else:
        for role in ROLE_KEYWORDS:
            result["agents"][role] = None

    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
