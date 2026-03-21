#!/usr/bin/env python3
from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

import detect_host_env


def wsl_path(win_path: Path) -> str:
    proc = subprocess.run(['wsl.exe', 'wslpath', '-a', str(win_path)], capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or 'Failed to convert path through wslpath')
    return proc.stdout.strip()


def main(argv: list[str]) -> int:
    tool_root = Path(__file__).resolve().parent
    project_root = Path(os.environ.get('BMADX_PROJECT_ROOT') or tool_root.parent.parent).resolve()
    env = detect_host_env.detect(project_root)
    detect_host_env.write_state(project_root, env)

    mode = env['preferred_mode']
    if mode == 'windows-wsl':
        project_wsl = wsl_path(project_root)
        tool_wsl = wsl_path(tool_root)
        extra = ' '.join(shlex.quote(x) for x in argv[1:])
        cmd = [
            'wsl.exe', 'bash', '-lc',
            f'export BMADX_PROJECT_ROOT="{project_wsl}"; '
            f'export BMADX_TOOL_ROOT="{tool_wsl}"; '
            f'bash "{tool_wsl}/run.sh" {extra}'
        ]
        return subprocess.run(cmd).returncode

    if mode == 'windows-native-limited':
        print('[BMADX] Windows native mode is limited. Install WSL and rerun run.py.')
        return 1

    cmd = ['bash', str(tool_root / 'run.sh'), *argv[1:]]
    env_vars = {**os.environ, 'BMADX_PROJECT_ROOT': str(project_root), 'BMADX_TOOL_ROOT': str(tool_root)}
    return subprocess.run(cmd, env=env_vars).returncode


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
