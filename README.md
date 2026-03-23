# bmad-codex

BMAD persona/workflow adapter for Codex-driven project automation.

이 저장소는 **기존 프로젝트 내부**에 `tools/bmad-codex`로 clone해서 사용합니다.

```bash
mkdir -p tools
git clone <THIS_REPO_URL> tools/bmad-codex
```

기존 적용 프로젝트 업그레이드 방법은 [UPGRADE.md](./UPGRADE.md)를 참고하세요.

## 핵심 변경점

v6부터는 실행 전에 운영 환경을 먼저 감지하고, 그 결과를 `.bmadx/state/host-env.json`에 기록합니다.

- Linux / macOS / WSL 런타임이면 네이티브 실행
- Windows면 **usable WSL**인지 먼저 검사
- usable WSL이 없으면 Windows native readiness를 검사
- 둘 다 불충분하면 무리하게 진행하지 않고 명확한 진단 메시지와 함께 중단

즉, 이제는 `wsl.exe`가 있다는 이유만으로 `windows-wsl`로 결정하지 않습니다.

## 권장 진입점

항상 Python 런처부터 실행하세요.

### Linux / macOS / WSL

```bash
python3 tools/bmad-codex/bootstrap.py
python3 tools/bmad-codex/run.py
```

### Windows PowerShell

```powershell
py -3 .\tools\bmad-codex\bootstrap.py
py -3 .\tools\bmad-codex\run.py
```

또는:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\bmad-codex\bootstrap.ps1
powershell -ExecutionPolicy Bypass -File .\tools\bmad-codex\run.ps1
```

## Windows 실행 정책

Windows에서는 아래 순서로 실행 모드를 선택합니다.

1. **windows-wsl**
   - usable Linux distro가 실제로 설치되어 있고
   - WSL 내부에 `bash`, `python3`, `git`, `codex`가 모두 있을 때만 사용
2. **windows-native**
   - WSL이 준비되지 않았지만 Windows 쪽에서 `bash`, Python 3, `git`, `codex`가 모두 정상 동작할 때만 사용
3. **windows-native-limited**
   - 위 둘 다 준비되지 않았을 때
   - 이 경우 런처는 진행하지 않고 준비 체크리스트를 출력합니다

## Windows readiness 체크리스트

PowerShell에서 아래를 먼저 확인하면 좋습니다.

```powershell
wsl -l -v
wsl -d Ubuntu-24.04 -- bash -lc "python3 --version && git --version && codex --version"
```

정상적인 WSL 사용을 위해서는 단순히 `wsl.exe`가 있는 것만으로는 부족합니다.
**실제로 사용 가능한 Linux distro**가 있어야 하고, 그 안에 아래 명령이 있어야 합니다.

- `bash`
- `python3`
- `git`
- `codex`

`docker-desktop`만 있고 일반 Linux distro가 없으면 `windows-wsl`로 진행하지 않습니다.
런처를 실행한 뒤에는 `.bmadx/state/host-env.json`에서 아래 값도 확인하세요.

- `preferred_mode: windows-wsl`
- `wsl.ready: true`
- `wsl.requirements.bash/python3/git/codex: true`

## Git Bash에 대한 권장 사항

Git Bash는 보조 수단일 뿐입니다.

- bootstrap 일부는 Git Bash에서 돌아갈 수 있습니다
- 하지만 Codex CLI 실행 권한, Python 경로, WindowsApps 권한 문제로 인해 `run` 단계는 쉽게 깨질 수 있습니다
- 따라서 Windows에서는 **Git Bash 직접 실행보다 Python 런처 또는 PowerShell 래퍼를 통한 WSL 위임**을 권장합니다

## host-env.json

부트스트랩은 `.bmadx/state/host-env.json`을 작성합니다.
이 파일은 실행 환경의 소스 오브 트루스입니다.

예시 항목:

- `host.os`
- `host.shell`
- `preferred_mode`
- `wsl.usable_distro`
- `wsl.requirements`
- `native.bash/python/git/codex`
- `execution.python_cmd`
- `execution.bash_cmd`
- `execution.codex_cmd`
- `readiness_messages`

LLM은 운영체제를 추측하지 말고, 이 파일을 읽고 그에 맞는 경로로 진행해야 합니다.

## bootstrap이 하는 일

- `.bmadx/state/host-env.json` 생성
- `.bmadx/state/runtime-manifest.json` 생성
- `.bmadx/state/install-context.json` 생성
- `.bmadx/state/sprint-status.path` 갱신
- `.codex/agents/bmadx-*.toml` 설치
- `.agents/skills/bmadx-*` 설치
- `scripts/bmadx/*` 설치
- `scripts/gates/*` 설치
- `AGENTS.override.md`에 BMADX 관리 블록 추가

기존 `bmad-*` 스킬은 유지하고, 이 패키지는 `bmadx-*`만 설치합니다.

## 자동 진행 방식

`run.py` 또는 `run.sh`는 BMAD sprint status를 읽고 다음 단계를 자동으로 선택합니다.

지원 상태 흐름:

- `backlog` -> SM 스토리 생성 -> PM/PO 검토
- `drafted` 또는 `ready-for-dev` -> DEV
- `in-progress` -> DEV 계속
- `review` -> QA
- `done` -> 다음 스토리

상태 파일 탐색 위치:

- `.bmad-ephemeral/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- 그 외 일반적인 BMAD 출력 경로 fallback

상태 파일이 없으면 planning artifacts를 바탕으로 생성 시도합니다.

## Codex 실행 관련

오케스트레이터는 `.bmadx/state/host-env.json`의 `execution.codex_cmd`를 읽습니다.
또한 `BMADX_CODEX` 환경변수로 Codex 실행 파일을 강제할 수 있습니다.

예:

```bash
BMADX_CODEX=/usr/local/bin/codex python3 tools/bmad-codex/run.py
```

Windows에서도 native mode가 충분히 준비된 경우:

```powershell
$env:BMADX_CODEX = "C:\path\to\codex.exe"
py -3 .\tools\bmad-codex\run.py
```

## 실패 시 확인 순서

1. `tools/bmad-codex/bootstrap.py` 실행
2. `.bmadx/state/host-env.json` 확인
3. `.bmadx/state/runtime-manifest.json` 확인
4. `.bmadx/state/install-context.json` 확인
5. `.bmadx/state/sprint-status.path` 확인
6. `.bmadx/state/last-codex-*.raw.log` 확인
7. `.bmadx/state/last-gate-*.log` 확인

Windows에서 WSL 안 `codex`가 비어 있거나 깨져 있다면, 이 starter에 특정 Desktop 앱 경로를 하드코딩하지는 마세요. 이 저장소는 **WSL 안에서 `codex`가 정상 실행 가능하다는 전제**만 두고, 실제 브리지는 각 환경에서 별도로 준비하는 쪽이 안전합니다.

## 코딩 LLM용 표준 지시문

```text
Current directory is the project root.
If tools/bmad-codex is missing, clone <THIS_REPO_URL> into tools/bmad-codex.
Read tools/bmad-codex/README.md and tools/bmad-codex/LLM_QUICKSTART.md.
Run the Python launcher, not raw shell scripts first:
- Linux/macOS/WSL: python3 tools/bmad-codex/bootstrap.py
- Windows: py -3 .\tools\bmad-codex\bootstrap.py
Then read .bmadx/state/host-env.json and .bmadx/state/runtime-manifest.json.
Use preferred_mode and the recorded execution commands instead of guessing OS-specific commands.
If bootstrap fails, inspect readiness_messages and fix the environment before retrying.
Then run the matching launcher for run.py.
Let the orchestrator choose the next story from sprint-status.yaml automatically.
Never mark work complete unless the corresponding gate script exits 0.
```
