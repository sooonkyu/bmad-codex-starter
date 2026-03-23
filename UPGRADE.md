# Upgrade Guide

기존 BMADX 적용 프로젝트를 최신 버전으로 올릴 때 참고하는 문서입니다.

## TL;DR

- 새 프로젝트에 이 starter를 새로 clone해서 쓰는 경우:
  - 최신 `main`을 받으면 대부분 바로 반영됩니다.
- 이미 다른 프로젝트에 `tools/bmad-codex`로 붙여서 쓰고 있는 경우:
  - `git pull`만으로는 부족할 수 있습니다.
  - 이유는 실제 실행 파일들이 대상 프로젝트 안으로 복사되거나 링크되기 때문입니다.
  - 최신 starter를 받은 뒤 대상 프로젝트에서 `bootstrap` 또는 `install.sh`를 다시 실행해야 합니다.

## 이번 업그레이드에서 강화된 점

### 1. Windows + Codex + WSL 실행 안정성 강화

- `wsl.exe`가 있다고 바로 WSL ready로 간주하지 않습니다.
- WSL 내부에서 `bash`, `python3`, `git`, `codex`가 실제로 동작하는지 확인합니다.
- Windows에서 WSL 실행 시 `bash -lc` + 실제 WSL 프로젝트 경로로 진입한 뒤 명령을 실행합니다.
- `host-env.json`의 `execution.*` 값이 더 신뢰할 수 있는 형태로 기록됩니다.

### 2. 오케스트레이션 phase가 더 명확해짐

이전보다 phase가 분리되어, 어디서 멈췄는지와 다음 단계가 더 분명해졌습니다.

- `create-story`
- `validate-story`
- `revise-story`
- `dev-story`
- `code-review`
- `qa-verify`
- `retrospective`

### 3. phase 상태가 영속적으로 저장됨

새 파일:

- `.bmadx/state/orchestration-state.json`

이 파일에 현재 스토리, 현재 phase, attempt, history가 저장됩니다.
따라서 실패 후 재실행해도 같은 phase에서 이어가기 쉬워졌습니다.

### 4. 게이트가 더 엄격해짐

이제 단순 명령 실행뿐 아니라 리뷰 산출물 자체도 읽습니다.

- story gate:
  - story 파일 존재 여부
  - 필수 섹션 존재 여부
  - 체크박스 task 존재 여부
  - PM/PO 승인 여부
- code review gate:
  - `.bmadx/reviews/{story}.code-review.md`
  - `Verdict: PASS/FAIL` 확인
- qa verify gate:
  - `.bmadx/reviews/{story}.qa-report.md`
  - `Verdict: PASS/FAIL` 확인
  - integration/e2e/build 명령 실행

새 스크립트:

- `scripts/gates/code_review_gate.sh`

### 5. 멀티 런타임 탐지 강화

이전처럼 Node 하나 또는 Python 하나만 보는 구조가 아니라, 여러 workspace를 수집할 수 있게 보강됐습니다.

예:

- root Node app
- `frontend/`
- `web/`
- `app/`
- `apps/*`
- root Python app
- `backend/`
- `api/`
- `services/*`

결과는 `.bmadx/state/runtime-manifest.json`의 `workspaces`와 command list에 반영됩니다.

### 6. `docs/`는 실행 대상에서 제외됨

이번 버전부터 `docs/` 안의 sprint status나 planning artifacts는 실제 실행 대상에서 제외됩니다.

즉:

- `docs/`는 참고 문서
- 실제 orchestration 대상은 현재 프로젝트 본체

라는 전제가 코드에 반영됐습니다.

### 7. Git Bash / Windows Python 호환성 보강

Git Bash에서 `python3` here-doc이 깨지는 환경을 고려해:

- `install.sh`
- `bootstrap.sh`
- `run.sh`

에서 Python 선택 시 `py`를 우선 사용할 수 있게 보강했습니다.

## 기존 적용 프로젝트 업그레이드 방법

여기서 "대상 프로젝트"는 실제 서비스 코드가 있는 프로젝트를 말합니다.
예를 들어:

- `my-project/tools/bmad-codex`

처럼 이 starter를 내부에 clone해 둔 프로젝트입니다.

### 1. starter 업데이트

대상 프로젝트 안의 starter 경로로 이동해서 최신 버전을 받습니다.

```bash
cd tools/bmad-codex
git pull origin main
```

### 2. 대상 프로젝트 루트로 돌아가서 재설치

중요:
`git pull`은 starter 저장소 파일만 업데이트합니다.
하지만 실제로 Codex가 읽는 파일들 중 일부는 대상 프로젝트 안으로 복사되거나 링크됩니다.

따라서 아래 중 하나를 다시 실행해야 합니다.

Linux / macOS / WSL:

```bash
python3 tools/bmad-codex/bootstrap.py
```

Windows PowerShell:

```powershell
py -3 .\tools\bmad-codex\bootstrap.py
```

또는:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\bmad-codex\bootstrap.ps1
```

### 3. 실제로 갱신되는 파일 확인

재설치 후 대상 프로젝트에서 아래 파일들이 최신 버전으로 반영됩니다.

- `.codex/agents/bmadx-*.toml`
- `.agents/skills/bmadx-*`
- `scripts/bmadx/*`
- `scripts/gates/*`
- `AGENTS.override.md`
- `.bmadx/state/host-env.json`
- `.bmadx/state/runtime-manifest.json`
- `.bmadx/state/sprint-status.path`

### 4. 새 상태 파일 확인

이번 버전에서는 아래 파일도 중요합니다.

- `.bmadx/state/orchestration-state.json`

없다면 한 번 `run.py`를 실행해 생성되는지 확인하세요.

## 업그레이드 후 추천 검증 순서

### 1. host-env 확인

```bash
cat .bmadx/state/host-env.json
```

Windows라면 특히 아래를 봅니다.

- `preferred_mode`
- `wsl.ready`
- `wsl.requirements`
- `execution.python_cmd`
- `execution.bash_cmd`
- `execution.codex_cmd`

### 2. runtime manifest 확인

```bash
cat .bmadx/state/runtime-manifest.json
```

확인 포인트:

- `runtime.primary`
- `runtime.detected`
- `workspaces`
- `commands.install/lint/typecheck/test/build`

### 3. 새 gate 파일 확인

아래 파일이 있어야 이번 버전이 정상 반영된 것입니다.

- `scripts/gates/code_review_gate.sh`

### 4. orchestrator 1회 실행

Linux / macOS / WSL:

```bash
python3 tools/bmad-codex/run.py --max-cycles 1
```

Windows:

```powershell
py -3 .\tools\bmad-codex\run.py --max-cycles 1
```

이후 아래 파일들을 확인합니다.

- `.bmadx/state/planner.json`
- `.bmadx/state/orchestration-state.json`
- `.bmadx/state/last-codex-*.raw.log`
- `.bmadx/state/last-gate-*.log`

## 운영 중 주의점

### `git pull`만으로는 끝나지 않을 수 있음

대상 프로젝트가 이미 아래 파일들을 가지고 있다면:

- `.codex/agents/*`
- `.agents/skills/*`
- `scripts/bmadx/*`
- `scripts/gates/*`

starter만 pull하고 대상 프로젝트에 재설치를 하지 않으면, 실제 실행은 예전 템플릿으로 계속 돌 수 있습니다.

### 기존 세션을 이어가고 싶지 않다면

role별 Codex 세션 재개가 부담되면 아래 파일을 지우고 새로 시작할 수 있습니다.

- `.bmadx/state/sessions.json`

### stale 상태를 산출물에 박지 않도록 주의

이번 버전은 phase를 더 엄격하게 추적합니다.
그래서 story나 dev note 같은 영속 문서에는 현재 phase나 현재 sprint status를 확정 문장으로 오래 남겨두지 않는 편이 안전합니다.

## 팀에 전달할 때 쓸 짧은 요약

필요하면 아래 문장을 그대로 공유해도 됩니다.

```text
BMADX starter를 최신 버전으로 올렸습니다.
이번 버전은 Windows+WSL Codex 실행 안정성, orchestration-state 영속화, code-review/qa-verify phase 분리, 강화된 gate, 멀티 runtime discovery, docs 제외 처리, Git Bash 호환성 보강이 포함됩니다.
기존 프로젝트는 tools/bmad-codex git pull만 하지 말고, 프로젝트 루트에서 bootstrap을 다시 실행해 템플릿과 gate를 갱신해 주세요.
```
