#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import locale
import os
import platform
import re
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


def run_capture_bytes(cmd: list[str], timeout: int = 8) -> tuple[int, bytes, bytes]:
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout)
        return proc.returncode, proc.stdout or b'', proc.stderr or b''
    except FileNotFoundError as exc:
        return 127, b'', str(exc).encode('utf-8', errors='replace')
    except PermissionError as exc:
        return 126, b'', str(exc).encode('utf-8', errors='replace')
    except subprocess.TimeoutExpired as exc:
        return 124, exc.stdout or b'', exc.stderr or b'timeout'
    except Exception as exc:
        return 125, b'', str(exc).encode('utf-8', errors='replace')


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


def choose_windows_bash_cmd() -> list[str]:
    override = os.environ.get('BMADX_BASH', '').strip()
    if override:
        return shlex.split(override)
    for candidate in (
        r'C:\Program Files\Git\bin\bash.exe',
        r'C:\Program Files (x86)\Git\bin\bash.exe',
    ):
        if Path(candidate).exists():
            return [candidate]
    return ['bash']


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


def clean_windows_output_text(text: str) -> str:
    return text.replace('\x00', '').replace('\ufeff', '')


def decode_windows_output(data: bytes, prefer_utf16: bool = False) -> str:
    if not data:
        return ''
    encodings: list[str] = []
    utf16_hint = prefer_utf16 or b'\x00' in data or data.startswith((b'\xff\xfe', b'\xfe\xff'))
    if utf16_hint:
        encodings.append('utf-16le')
    preferred = locale.getpreferredencoding(False) or 'utf-8'
    encodings.extend(['utf-8-sig', preferred, 'utf-8', 'cp949'])

    seen: set[str] = set()
    for encoding in encodings:
        if encoding in seen:
            continue
        seen.add(encoding)
        try:
            return clean_windows_output_text(data.decode(encoding))
        except UnicodeDecodeError:
            continue
    return clean_windows_output_text(data.decode('utf-8', errors='replace'))


def parse_wsl_list(output: str) -> dict[str, Any]:
    output = clean_windows_output_text(output)
    distros: list[dict[str, Any]] = []
    default_name = None
    lines = [raw.rstrip() for raw in output.splitlines() if raw.strip()]
    header = next(
        (line for line in lines if 'name' in line.lower() and 'state' in line.lower() and 'version' in line.lower()),
        '',
    )
    state_col = header.lower().find('state') if header else -1
    version_col = header.lower().find('version') if header else -1

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            continue
        lower = line.lower().strip()
        if lower.startswith('windows subsystem for linux') or lower.startswith('the following is a list'):
            continue
        if lower.startswith('name') and 'state' in lower and 'version' in lower:
            continue
        is_default = line.lstrip().startswith('*')
        cleaned = line.replace('*', ' ', 1) if is_default else line

        columns = [part.strip() for part in re.split(r'\s{2,}', cleaned.strip()) if part.strip()]
        if len(columns) >= 3:
            name = columns[0]
            state = columns[1]
            version = columns[2]
        elif state_col > 0 and version_col > state_col:
            name = cleaned[:state_col].strip()
            state = cleaned[state_col:version_col].strip()
            version = cleaned[version_col:].strip()
        else:
            parts = cleaned.strip().split()
            if len(parts) >= 3:
                name = ' '.join(parts[:-2])
                state = parts[-2]
                version = parts[-1]
            elif len(parts) == 2:
                name = parts[0]
                state = parts[1]
                version = ''
            elif len(parts) == 1:
                name = parts[0]
                state = ''
                version = ''
            else:
                name = ''
                state = ''
                version = ''

        if not name:
            continue
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
    rc, out, _ = run_capture_bytes(['wsl.exe', '-l', '-q'], timeout=8)
    if rc != 0:
        return []
    text = decode_windows_output(out)
    names = []
    for raw in text.splitlines():
        name = clean_windows_output_text(raw).strip()
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

    rc, out_bytes, err_bytes = run_capture_bytes(['wsl.exe', '-l', '-v'], timeout=8)
    out = decode_windows_output(out_bytes)
    err = decode_windows_output(err_bytes)
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
    probe_script = '; '.join([
        'printf "bash="; if command -v bash >/dev/null 2>&1; then echo 1; else echo 0; fi',
        'printf "python3="; if command -v python3 >/dev/null 2>&1; then echo 1; else echo 0; fi',
        'printf "git="; if command -v git >/dev/null 2>&1; then echo 1; else echo 0; fi',
        'printf "codex="; if bash -lc "codex --version >/dev/null 2>&1"; then echo 1; else echo 0; fi',
    ])
    rc, out_bytes, err_bytes = run_capture_bytes(['wsl.exe', '-d', distro, '--', 'sh', '-lc', probe_script], timeout=12)
    out = decode_windows_output(out_bytes)
    err = decode_windows_output(err_bytes)
    data['diagnostics']['probe_stdout'] = out.strip()
    data['diagnostics']['probe_stderr'] = err.strip()
    if rc != 0:
        return data

    found = {}
    for line in clean_windows_output_text(out).splitlines():
        if '=' not in line:
            continue
        key, value = line.strip().split('=', 1)
        found[key] = value == '1'
    for req in data['requirements']:
        data['requirements'][req] = bool(found.get(req, False))
    data['ready'] = all(data['requirements'].values())
    return data


def probe_windows_native() -> dict[str, Any]:
    bash_cmd = choose_windows_bash_cmd()
    python_cmd = choose_windows_python_cmd()
    codex_cmd = choose_windows_codex_cmd()
    python_ok = windows_command_health([*python_cmd, '--version'])
    git_ok = windows_command_health(['git', '--version']) if cmd_exists('git') else {
        'command': ['git', '--version'], 'ok': False, 'returncode': 127, 'stdout': '', 'stderr': 'git not found'
    }
    bash_ok = windows_command_health([*bash_cmd, '--version'])
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


def windows_to_wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(':').lower()
    tail = resolved.as_posix().split(':', 1)[-1].lstrip('/')
    if drive:
        return f'/mnt/{drive}/{tail}'
    return resolved.as_posix()


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


def build_execution(project_root: Path, tool_root: Path, mode: str, wsl: dict[str, Any], native: dict[str, Any]) -> dict[str, Any]:
    tool_path = tool_root.resolve()
    if mode == 'windows-wsl':
        distro = wsl.get('usable_distro')
        bash_cmd = ['wsl.exe', '-d', distro, '--', 'bash']
        python_cmd = ['wsl.exe', '-d', distro, '--', 'python3']
        codex_cmd = ['wsl.exe', '-d', distro, '--', 'codex']
        project_wsl = windows_to_wsl_path(project_root)
        tool_wsl = windows_to_wsl_path(tool_path)
        bootstrap_native = [
            'wsl.exe', '-d', distro, '--', 'bash', '-lc',
            f'export BMADX_PROJECT_ROOT={shlex.quote(project_wsl)}; '
            f'export BMADX_TOOL_ROOT={shlex.quote(tool_wsl)}; '
            f'bash {shlex.quote(tool_wsl + "/bootstrap.sh")}'
        ]
        run_native = [
            'wsl.exe', '-d', distro, '--', 'bash', '-lc',
            f'export BMADX_PROJECT_ROOT={shlex.quote(project_wsl)}; '
            f'export BMADX_TOOL_ROOT={shlex.quote(tool_wsl)}; '
            f'bash {shlex.quote(tool_wsl + "/run.sh")}'
        ]
    elif mode == 'windows-native':
        bash_cmd = choose_windows_bash_cmd()
        python_cmd = choose_windows_python_cmd()
        codex_cmd = choose_windows_codex_cmd()
        bootstrap_native = [*bash_cmd, str(tool_path / 'bootstrap.sh')]
        run_native = [*bash_cmd, str(tool_path / 'run.sh')]
    elif mode == 'windows-native-limited':
        bash_cmd = choose_windows_bash_cmd() if (os.environ.get('BMADX_BASH') or Path(r'C:\Program Files\Git\bin\bash.exe').exists() or Path(r'C:\Program Files (x86)\Git\bin\bash.exe').exists() or cmd_exists('bash')) else []
        python_cmd = choose_windows_python_cmd() if (cmd_exists('py') or cmd_exists('python')) else []
        codex_cmd = choose_windows_codex_cmd()
        bootstrap_native = [*bash_cmd, str(tool_path / 'bootstrap.sh')] if bash_cmd else []
        run_native = [*bash_cmd, str(tool_path / 'run.sh')] if bash_cmd else []
    else:
        bash_cmd = ['bash']
        python_cmd = [shutil.which('python3') or shutil.which('python') or 'python3']
        codex_cmd = resolve_linux_like_codex()
        bootstrap_native = [*bash_cmd, str(tool_path / 'bootstrap.sh')]
        run_native = [*bash_cmd, str(tool_path / 'run.sh')]

    return {
        'python_cmd': python_cmd,
        'bash_cmd': bash_cmd,
        'codex_cmd': codex_cmd,
        'bootstrap_native': bootstrap_native,
        'run_native': run_native,
    }


def detect(project_root: Path, tool_root: Path | None = None) -> dict:
    system = platform.system().lower()
    os_name = {'windows': 'windows', 'darwin': 'macos', 'linux': 'linux'}.get(system, system)
    tool_root = (tool_root or Path(os.environ.get('BMADX_TOOL_ROOT') or (project_root / 'tools' / 'bmad-codex'))).resolve()
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
        'execution': build_execution(project_root, tool_root, mode, wsl, native),
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
