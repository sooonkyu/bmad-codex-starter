# LLM quickstart

## Goal

현재 프로젝트 루트에 이 어댑터를 설치하고, host-env 기반으로 안전하게 실행해서 BMAD sprint status에 따라 다음 단계를 자동 진행합니다.

## Standard assumptions

- 현재 디렉터리는 프로젝트 루트입니다.
- 이 저장소는 `tools/bmad-codex`에 있어야 합니다.
- BMAD 파일은 `_bmad/`, `_bmad-output/`, `.bmad-ephemeral/` 아래에 있을 수 있습니다.

## Required sequence for a coding LLM

1. `tools/bmad-codex`가 없으면 이 저장소를 그 경로로 clone 합니다.
2. `tools/bmad-codex/README.md`를 읽습니다.
3. 먼저 Python 런처를 실행합니다.
   - Linux/macOS/WSL: `python3 tools/bmad-codex/bootstrap.py`
   - Windows: `py -3 .\tools\bmad-codex\bootstrap.py`
4. `.bmadx/state/host-env.json`을 읽습니다.
5. `.bmadx/state/runtime-manifest.json`을 읽습니다.
6. `preferred_mode`, `execution.*`, `readiness_messages`를 기준으로만 다음 명령을 선택합니다.
7. 운영체제를 추측해서 임의 명령을 만들지 않습니다.
8. bootstrap이 실패하면 환경 문제를 먼저 수정한 뒤 다시 실행합니다.
9. 그 다음 matching Python 런처로 `run.py`를 실행합니다.
10. `sprint-status.yaml`을 보고 오케스트레이터가 다음 스토리를 자동 선택하게 둡니다.

## Windows rule

- `wsl.exe`가 있다고 해서 곧바로 WSL 준비 완료라고 판단하지 않습니다.
- usable Linux distro와 WSL 내부 `bash/python3/git/codex`가 모두 있을 때만 `windows-wsl`을 사용합니다.
- 그 외에는 `host-env.json`의 진단 메시지를 먼저 확인합니다.
- Windows에서는 raw Git Bash 명령보다 Python 런처를 우선 사용합니다.

## Done criteria

- `bootstrap.py`가 성공적으로 끝납니다.
- `.bmadx/state/host-env.json`이 생성됩니다.
- `.bmadx/state/runtime-manifest.json`이 생성됩니다.
- `.bmadx/state/planner.json`이 orchestration 중 갱신됩니다.
- 완료를 주장하기 전에 해당 gate script exit code가 0입니다.
