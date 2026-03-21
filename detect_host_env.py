#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
from pathlib import Path


def cmd_exists(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def detect_shell() -> str:
    if os.name == 'nt':
        if os.environ.get('MSYSTEM'):
            return 'git-bash'
        if os.environ.get('PSModulePath'):
            return 'powershell'
        comspec = os.environ.get('ComSpec', '').lower()
        if 'cmd.exe' in comspec:
            return 'cmd'
        return 'windows-unknown'
    shell = os.environ.get('SHELL', '').lower()
    if 'zsh' in shell:
        return 'zsh'
    if 'bash' in shell:
        return 'bash'
    return 'posix-unknown'


def is_wsl_runtime() -> bool:
    if os.environ.get('WSL_INTEROP') or os.environ.get('WSL_DISTRO_NAME'):
        return True
    try:
        text = Path('/proc/version').read_text(encoding='utf-8', errors='ignore').lower()
        return 'microsoft' in text or 'wsl' in text
    except Exception:
        return False


def wsl_available() -> bool:
    return platform.system().lower() == 'windows' and (cmd_exists('wsl.exe') or cmd_exists('wsl'))


def resolve_codex_executable() -> list[str]:
    override = os.environ.get('BMADX_CODEX', '').strip()
    if override:
        return [override]
    if cmd_exists('codex'):
        return ['codex']
    if platform.system().lower() == 'windows' and wsl_available():
        return ['wsl.exe', 'codex']
    return ['codex']


def preferred_mode() -> str:
    system = platform.system().lower()
    if system == 'windows':
        return 'windows-wsl' if wsl_available() else 'windows-native-limited'
    if system == 'darwin':
        return 'native-macos'
    if system == 'linux':
        return 'native-linux'
    return f'native-{system or "unknown"}'


def detect(project_root: Path) -> dict:
    system = platform.system().lower()
    os_name = {'windows': 'windows', 'darwin': 'macos', 'linux': 'linux'}.get(system, system)
    mode = preferred_mode()

    if mode.startswith('native-'):
        bash_cmd = ['bash']
        python_cmd = [shutil.which('python3') or shutil.which('python') or 'python3']
    elif mode == 'windows-wsl':
        bash_cmd = ['wsl.exe', 'bash']
        python_cmd = ['wsl.exe', 'python3']
    else:
        bash_cmd = ['bash'] if cmd_exists('bash') else []
        python_cmd = [shutil.which('python') or 'python']

    return {
        'host': {
            'os': os_name,
            'shell': detect_shell(),
            'is_wsl_runtime': is_wsl_runtime(),
            'is_git_bash': bool(os.environ.get('MSYSTEM')),
            'wsl_available': wsl_available(),
        },
        'preferred_mode': mode,
        'execution': {
            'python_cmd': python_cmd,
            'bash_cmd': bash_cmd,
            'codex_cmd': resolve_codex_executable(),
            'bootstrap_native': ['bash', str((project_root / 'tools' / 'bmad-codex' / 'bootstrap.sh').as_posix())],
            'run_native': ['bash', str((project_root / 'tools' / 'bmad-codex' / 'run.sh').as_posix())],
        },
    }


def write_state(project_root: Path, data: dict) -> Path:
    out = project_root / '.bmadx' / 'state' / 'host-env.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--project-root', default=os.environ.get('BMADX_PROJECT_ROOT') or str(Path.cwd()))
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    data = detect(project_root)
    if args.write:
        print(write_state(project_root, data))
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
