#!/usr/bin/env python3
from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

import detect_host_env


def windows_to_wsl_path(path: Path) -> str:
    resolved = str(path.resolve())
    if len(resolved) >= 2 and resolved[1] == ':':
        drive = resolved[0].lower()
        tail = resolved[2:].replace('\\', '/').lstrip('/')
        return f'/mnt/{drive}/{tail}' if tail else f'/mnt/{drive}'
    return resolved.replace('\\', '/')


def print_readiness(env: dict) -> None:
    print('[BMADX] run launcher cannot continue in the current host environment.')
    for msg in env.get('readiness_messages', []):
        print(f'[BMADX] {msg}')
    wsl = env.get('wsl', {})
    if wsl.get('installed'):
        print(f"[BMADX] WSL usable distro: {wsl.get('usable_distro')!r}")
        print(f"[BMADX] WSL requirements: {wsl.get('requirements')}")
    native = env.get('native', {})
    if native:
        print(f"[BMADX] Native checks: bash={native.get('bash', {}).get('ok')}, python={native.get('python', {}).get('ok')}, git={native.get('git', {}).get('ok')}, codex={native.get('codex', {}).get('ok')}")
        codex_err = native.get('codex', {}).get('stderr')
        if codex_err:
            print(f'[BMADX] Native codex stderr: {codex_err}')


def main(argv: list[str]) -> int:
    tool_root = Path(__file__).resolve().parent
    project_root = Path(os.environ.get('BMADX_PROJECT_ROOT') or tool_root.parent.parent).resolve()
    env = detect_host_env.detect(project_root)
    detect_host_env.write_state(project_root, env)

    mode = env['preferred_mode']
    env_vars = {**os.environ, 'BMADX_PROJECT_ROOT': str(project_root), 'BMADX_TOOL_ROOT': str(tool_root)}

    if mode == 'windows-wsl':
        distro = env.get('wsl', {}).get('usable_distro')
        if not distro:
            print_readiness(env)
            return 1
        project_wsl = windows_to_wsl_path(project_root)
        tool_wsl = windows_to_wsl_path(tool_root)
        extra = ' '.join(shlex.quote(x) for x in argv[1:])
        cmd = [
            'wsl.exe', '-d', distro, '--', 'bash', '-lc',
            f'export BMADX_PROJECT_ROOT="{project_wsl}"; '
            f'export BMADX_TOOL_ROOT="{tool_wsl}"; '
            f'bash "{tool_wsl}/run.sh" {extra}'
        ]
        return subprocess.run(cmd, env=env_vars).returncode

    if mode == 'windows-native':
        native = env.get('native', {})
        if not native.get('bash', {}).get('ok') or not native.get('codex', {}).get('ok'):
            print_readiness(env)
            return 1
        cmd = ['bash', str(tool_root / 'run.sh'), *argv[1:]]
        return subprocess.run(cmd, env=env_vars).returncode

    if mode == 'windows-native-limited':
        print_readiness(env)
        return 1

    cmd = ['bash', str(tool_root / 'run.sh'), *argv[1:]]
    return subprocess.run(cmd, env=env_vars).returncode


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
