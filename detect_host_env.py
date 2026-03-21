#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any


def cmd_exists(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def run_capture(cmd: list[str], timeout: int = 8) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout or '', proc.stderr or ''
    except FileNotFoundError as exc:
        return 127, '', str(exc)
    except PermissionError as exc:
        return 126, '', str(exc)
    except subprocess.TimeoutExpired as exc:
        return 124, exc.stdout or '', exc.stderr or 'timeout'
    except Exception as exc:
        return 125, '', str(exc)


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


def windows_command_health(cmd: list[str]) -> dict[str, Any]:
    rc, out, err = run_capture(cmd, timeout=8)
    return {
        'command': cmd,
        'ok': rc == 0,
        'returncode': rc,
        'stdout': out.strip(),
        'stderr': err.strip(),
    }


def choose_windows_python_cmd() -> list[str]:
    if cmd_exists('py'):
        return ['py', '-3']
    if cmd_exists('python'):
        return ['python']
    return ['python']


def choose_windows_codex_cmd() -> list[str]:
    override = os.environ.get('BMADX_CODEX', '').strip()
    if override:
        return shlex.split(override)
    for candidate in ('codex', 'codex.cmd', 'codex.exe'):
        if cmd_exists(candidate):
            return [candidate]
    return ['codex']


def parse_wsl_list(output: str) -> dict[str, Any]:
    distros: list[dict[str, Any]] = []
    default_name = None
    for raw in output.splitlines():
        line = raw.strip('\ufeff').rstrip()
        if not line.strip():
            continue
        lower = line.lower().strip()
        if lower.startswith('windows subsystem for linux') or lower.startswith('the following is a list'):
            continue
        if lower.startswith('name') and 'state' in lower and 'version' in lower:
            continue
        is_default = line.lstrip().startswith('*')
        cleaned = line.replace('*', ' ', 1).strip() if is_default else line.strip()
        parts = cleaned.split()
        if not parts:
            continue
        name = parts[0]
        state = parts[1] if len(parts) > 1 else ''
        version = parts[2] if len(parts) > 2 else ''
        info = {
            'name': name,
            'default': is_default,
            'state': state,
            'version': version,
            'is_docker': name.lower().startswith('docker-desktop'),
        }
        distros.append(info)
        if is_default:
            default_name = name
    usable = [d for d in distros if not d['is_docker']]
    selected = None
    if default_name:
        selected = next((d for d in usable if d['name'] == default_name), None)
    if selected is None and usable:
        selected = usable[0]
    return {
        'distros': distros,
        'usable_distro': selected['name'] if selected else None,
        'usable_distro_exists': selected is not None,
    }




def list_wsl_names() -> list[str]:
    rc, out, _ = run_capture(['wsl.exe', '-l', '-q'], timeout=8)
    if rc != 0:
        return []
    names = []
    for raw in out.splitlines():
        name = raw.strip().strip('\ufeff')
        if name:
            names.append(name)
    return names


def probe_wsl() -> dict[str, Any]:
    installed = platform.system().lower() == 'windows' and (cmd_exists('wsl.exe') or cmd_exists('wsl'))
    data: dict[str, Any] = {
        'installed': installed,
        'list_command_ok': False,
        'distros': [],
        'usable_distro_exists': False,
        'usable_distro': None,
        'ready': False,
        'requirements': {
            'bash': False,
            'python3': False,
            'git': False,
            'codex': False,
        },
        'diagnostics': {
            'list_stdout': '',
            'list_stderr': '',
            'probe_stdout': '',
            'probe_stderr': '',
        },
    }
    if not installed:
        return data

    rc, out, err = run_capture(['wsl.exe', '-l', '-v'], timeout=8)
    data['list_command_ok'] = rc == 0
    data['diagnostics']['list_stdout'] = out.strip()
    data['diagnostics']['list_stderr'] = err.strip()
    if rc != 0:
        return data

    parsed = parse_wsl_list(out)
    data['distros'] = parsed['distros']
    distro_names = [n for n in list_wsl_names() if not n.lower().startswith('docker-desktop')]
    distro = parsed['usable_distro'] or (distro_names[0] if distro_names else None)
    data['usable_distro_exists'] = distro is not None
    data['usable_distro'] = distro
    if not distro:
        return data
    probe_script = (
        'for c in bash python3 git codex; do '
        'if command -v "$c" >/dev/null 2>&1; then echo "$c=1"; else echo "$c=0"; fi; '
        'done'
    )
    rc, out, err = run_capture(['wsl.exe', '-d', distro, '--', 'bash', '-lc', probe_script], timeout=12)
    data['diagnostics']['probe_stdout'] = out.strip()
    data['diagnostics']['probe_stderr'] = err.strip()
    if rc != 0:
        return data

    found = {}
    for line in out.splitlines():
        if '=' not in line:
            continue
        key, value = line.strip().split('=', 1)
        found[key] = value == '1'
    for req in data['requirements']:
        data['requirements'][req] = bool(found.get(req, False))
    data['ready'] = all(data['requirements'].values())
    return data


def probe_windows_native() -> dict[str, Any]:
    python_cmd = choose_windows_python_cmd()
    codex_cmd = choose_windows_codex_cmd()
    python_ok = windows_command_health([*python_cmd, '--version'])
    git_ok = windows_command_health(['git', '--version']) if cmd_exists('git') else {
        'command': ['git', '--version'], 'ok': False, 'returncode': 127, 'stdout': '', 'stderr': 'git not found'
    }
    bash_ok = windows_command_health(['bash', '--version']) if cmd_exists('bash') else {
        'command': ['bash', '--version'], 'ok': False, 'returncode': 127, 'stdout': '', 'stderr': 'bash not found'
    }
    codex_ok = windows_command_health([*codex_cmd, '--version'])
    return {
        'bash': bash_ok,
        'python': python_ok,
        'git': git_ok,
        'codex': codex_ok,
        'ready': all(x['ok'] for x in (bash_ok, python_ok, git_ok, codex_ok)),
    }


def resolve_linux_like_codex() -> list[str]:
    override = os.environ.get('BMADX_CODEX', '').strip()
    if override:
        return shlex.split(override)
    return ['codex']


def preferred_mode(os_name: str, wsl: dict[str, Any], native: dict[str, Any]) -> str:
    if os_name == 'windows':
        if wsl.get('ready'):
            return 'windows-wsl'
        if native.get('ready'):
            return 'windows-native'
        return 'windows-native-limited'
    if os_name == 'macos':
        return 'native-macos'
    if os_name == 'linux':
        return 'native-linux'
    return f'native-{os_name or "unknown"}'


def build_execution(project_root: Path, mode: str, wsl: dict[str, Any], native: dict[str, Any]) -> dict[str, Any]:
    tool_path = project_root / 'tools' / 'bmad-codex'
    if mode == 'windows-wsl':
        distro = wsl.get('usable_distro')
        bash_cmd = ['wsl.exe', '-d', distro, '--', 'bash']
        python_cmd = ['wsl.exe', '-d', distro, '--', 'python3']
        codex_cmd = ['wsl.exe', '-d', distro, '--', 'codex']
    elif mode == 'windows-native':
        bash_cmd = ['bash']
        python_cmd = choose_windows_python_cmd()
        codex_cmd = choose_windows_codex_cmd()
    elif mode == 'windows-native-limited':
        bash_cmd = ['bash'] if cmd_exists('bash') else []
        python_cmd = choose_windows_python_cmd() if (cmd_exists('py') or cmd_exists('python')) else []
        codex_cmd = choose_windows_codex_cmd()
    else:
        bash_cmd = ['bash']
        python_cmd = [shutil.which('python3') or shutil.which('python') or 'python3']
        codex_cmd = resolve_linux_like_codex()

    return {
        'python_cmd': python_cmd,
        'bash_cmd': bash_cmd,
        'codex_cmd': codex_cmd,
        'bootstrap_native': ['bash', str((tool_path / 'bootstrap.sh').as_posix())],
        'run_native': ['bash', str((tool_path / 'run.sh').as_posix())],
    }


def detect(project_root: Path) -> dict:
    system = platform.system().lower()
    os_name = {'windows': 'windows', 'darwin': 'macos', 'linux': 'linux'}.get(system, system)
    wsl = probe_wsl() if os_name == 'windows' else {
        'installed': False,
        'list_command_ok': False,
        'distros': [],
        'usable_distro_exists': False,
        'usable_distro': None,
        'ready': False,
        'requirements': {'bash': False, 'python3': False, 'git': False, 'codex': False},
        'diagnostics': {'list_stdout': '', 'list_stderr': '', 'probe_stdout': '', 'probe_stderr': ''},
    }
    native = probe_windows_native() if os_name == 'windows' else {}
    mode = preferred_mode(os_name, wsl, native)

    readiness = []
    if os_name == 'windows' and mode == 'windows-native-limited':
        if wsl.get('installed') and not wsl.get('ready'):
            readiness.append('WSL exists but is not usable yet. Install a real Linux distro and ensure bash, python3, git, and codex are available inside WSL.')
        elif not wsl.get('installed'):
            readiness.append('WSL is not installed. Run `wsl --install` and install a Linux distro.')
        if native and not native.get('ready'):
            readiness.append('Windows native fallback is also not ready. bash, Python 3, git, and a healthy codex CLI are required for native execution.')

    return {
        'host': {
            'os': os_name,
            'shell': detect_shell(),
            'is_wsl_runtime': is_wsl_runtime(),
            'is_git_bash': bool(os.environ.get('MSYSTEM')),
        },
        'wsl': wsl,
        'native': native,
        'preferred_mode': mode,
        'execution': build_execution(project_root, mode, wsl, native),
        'readiness_messages': readiness,
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
