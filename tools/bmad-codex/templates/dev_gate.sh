#!/usr/bin/env bash
set -euo pipefail
STORY_KEY="${1:?story key required}"
python3 scripts/bmadx/gate.py dev "$STORY_KEY"
