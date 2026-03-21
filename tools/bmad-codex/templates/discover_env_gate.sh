#!/usr/bin/env bash
set -euo pipefail
python3 scripts/bmadx/discover_env.py
python3 scripts/bmadx/gate.py env
