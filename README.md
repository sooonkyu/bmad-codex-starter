# BMAD Codex Starter

BMAD 방식의 스토리 생성 → 검토 → 구현 → QA 루프를 **Codex 실행 환경**에서 자동으로 돌리기 위한 어댑터입니다.

이 GitHub 저장소 자체는 **패키지 파일이 저장소 루트에 바로 있는 평탄 구조**입니다. 실제 프로젝트에 설치할 때는 여전히 `tools/bmad-codex` 경로에 두는 방식을 권장합니다.

이 저장소는 다음을 목표로 합니다.

- BMAD의 agent/persona와 workflow를 최대한 참고
- Codex가 역할만 흉내 내지 않고 **실제 파일 수정과 실제 명령 실행**까지 수행
- `sprint-status.yaml`을 읽어 **다음 스토리를 자동 선택**
- 프로젝트의 기술 스택과 실행 명령을 먼저 파악한 뒤 DEV/QA를 수행
- Windows에서는 PowerShell 오류를 줄이기 위해 **WSL로 자동 위임**

---

## 어떻게 동작하나

이 어댑터는 프로젝트 안에 설치되면 아래 순서로 동작합니다.

1. BMAD 설치물(`_bmad`, `_bmad-output`)과 상태 파일(`sprint-status.yaml`)을 찾습니다.
2. 현재 프로젝트의 기술 스택과 실행 명령을 탐지합니다.
3. `.bmadx/state/runtime-manifest.json`에 install/lint/test/build 명령을 기록합니다.
4. `sprint-status.yaml`에서 현재 `ready-for-dev`, `in-progress`, `review` 상태의 스토리를 찾습니다.
5. BMAD agent 문서를 읽도록 Codex를 유도하고, 다음 루프를 실행합니다.
   - SM: 스토리 생성/수정
   - PM/PO: 스토리 검토
   - DEV: 구현
   - QA: 검증
6. 각 단계는 **gate script** 통과 여부로 완료 판정을 받습니다.
7. QA 실패 시 DEV로 되돌아가고, 완료 시 다음 스토리로 이동합니다.

---

## 저장소를 어디에 두나

이 저장소는 **실제 프로젝트 루트 아래 `tools/bmad-codex`** 로 들어가야 합니다.

참고로 GitHub 저장소 구조는 아래처럼 flat 합니다.

```text
repo-root/
├─ README.md
├─ LLM_QUICKSTART.md
├─ bootstrap.sh
├─ bootstrap.ps1
├─ run.sh
├─ run.ps1
├─ install.sh
├─ uninstall.sh
├─ orchestrator/
└─ templates/
```

예:

```bash
git clone <YOUR_REPO_URL> tools/bmad-codex
```

최종 구조 예시는 아래와 같습니다.

```text
my-project/
├─ _bmad/
├─ _bmad-output/
├─ tools/
│  └─ bmad-codex/
│     ├─ README.md
│     ├─ bootstrap.sh
│     ├─ bootstrap.ps1
│     ├─ run.sh
│     ├─ run.ps1
│     ├─ install.sh
│     ├─ uninstall.sh
│     ├─ orchestrator/
│     └─ templates/
├─ .bmadx/
├─ .agents/
└─ .codex/
```

---

## 요구 사항

### 공통

- Git
- Python 3
- Codex CLI 사용 가능 환경
- 프로젝트 루트에 파일 읽기/쓰기 권한

### Linux / macOS / WSL

- Bash

### Windows

- **WSL 설치 권장**
- PowerShell은 직접 bash 스크립트를 해석하지 않고, 이 저장소의 `bootstrap.ps1`, `run.ps1`가 **WSL로 자동 위임**합니다.

WSL이 없다면 먼저 설치하세요.

```powershell
wsl --install
```

설치 후 한 번 재부팅하거나 새 터미널을 여는 것이 안전합니다.

---

## 빠른 시작

### Linux / macOS / WSL

프로젝트 루트에서 실행:

```bash
mkdir -p tools
git clone <YOUR_REPO_URL> tools/bmad-codex
bash tools/bmad-codex/bootstrap.sh
bash tools/bmad-codex/run.sh
```

### Windows PowerShell

프로젝트 루트에서 실행:

```powershell
git clone <YOUR_REPO_URL> tools/bmad-codex
powershell -ExecutionPolicy Bypass -File .\tools\bmad-codex\bootstrap.ps1
powershell -ExecutionPolicy Bypass -File .\tools\bmad-codex\run.ps1
```

### 패키지 저장소 자체를 로컬에서 테스트할 때

저장소 루트에서 바로 확인 중이라면 아래처럼 실행해도 됩니다.

```bash
bash ./bootstrap.sh
bash ./run.sh
```

---

## 코딩 LLM에게 시킬 때 권장 프롬프트

아래 문구를 그대로 써도 됩니다.

```text
현재 디렉터리는 실제 프로젝트 루트다.

1. tools/bmad-codex 가 없으면 <YOUR_REPO_URL> 을 tools/bmad-codex 로 clone 해.
2. tools/bmad-codex/README.md 를 읽어.
3. Windows면 bootstrap.ps1 / run.ps1 을 사용하고, Linux/WSL이면 bootstrap.sh / run.sh 를 사용해.
4. 설치가 실패하면 원인을 수정한 뒤 다시 실행해.
5. 실행 중에는 BMAD의 sprint-status.yaml 을 읽어 다음 스토리를 자동 선택해.
6. 완료 판정은 실제 gate script 통과 기준으로만 내려.
7. 명령을 추측하지 말고 .bmadx/state/runtime-manifest.json 을 먼저 읽어.
```

---

## bootstrap과 run의 차이

### `bootstrap`

설치와 초기화만 담당합니다.

- 프로젝트 루트 판별
- `_bmad` 인덱싱
- `.agents/skills`, `.codex/agents` 설치
- `.bmadx/state/install-context.json` 생성
- 기술 스택 탐지
- `runtime-manifest.json` 생성
- `sprint-status.yaml` 탐색 또는 초기화

### `run`

실제 오케스트레이터를 실행합니다.

- `sprint-status.yaml`에서 현재 진행 대상 스토리 선택
- BMAD 상태에 따라 SM/PM/PO/DEV/QA 호출
- gate 통과 여부 확인
- 상태 업데이트
- 다음 스토리로 이동

---

## 상태 파일과 자동 진행 규칙

이 어댑터는 아래 위치를 우선적으로 확인합니다.

- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `.bmad-ephemeral/sprint-status.yaml`

상태값은 아래를 처리합니다.

- `backlog`
- `drafted`
- `ready-for-dev`
- `in-progress`
- `review`
- `done`

기본 규칙은 다음과 같습니다.

- `backlog` → SM이 스토리 초안 작성 후 PM/PO 검토
- `drafted`, `ready-for-dev` → DEV 구현 시작
- `in-progress` → DEV 계속
- `review` → QA 검증
- `done` → 다음 스토리로 이동

QA가 실패하면 해당 스토리를 다시 `in-progress` 흐름으로 되돌립니다.

---

## 기술 스택 탐지

초기 버전 기준으로 아래를 우선 지원합니다.

- Node.js
- Python
- Java
- Go
- Rust
- PHP

탐지 결과는 아래 파일에 저장됩니다.

```text
.bmadx/state/runtime-manifest.json
```

여기에는 보통 아래 정보가 들어갑니다.

- 주요 런타임
- 패키지 매니저
- install 명령
- lint 명령
- typecheck 명령
- test 명령
- build 명령
- migration / service bootstrap 명령

DEV와 QA는 **이 파일을 기준으로만 명령을 실행**해야 하며, 임의 추측으로 명령을 고르면 안 됩니다.

---

## 설치 시 생성되는 주요 파일

```text
.bmadx/
├─ state/
│  ├─ install-context.json
│  ├─ runtime-manifest.json
│  ├─ role-map.json
│  ├─ sessions.json
│  ├─ planner.json
│  ├─ last-gate-dev.log
│  ├─ last-gate-qa.log
│  └─ last-gate-story.log
├─ stories/
├─ reviews/
└─ runs/
```

### 설명

- `install-context.json` : 프로젝트 루트와 툴 루트 정보
- `runtime-manifest.json` : 실제 명령 계약
- `role-map.json` : `_bmad` 내부의 agent md 위치 인덱스
- `sessions.json` : 역할별 Codex 세션 정보
- `planner.json` : 현재 선택된 story/epic 상태 정보
- `last-gate-*.log` : 마지막 검증 로그

---

## 기존 BMAD 스킬과 충돌하나

충돌을 줄이기 위해 이 저장소는 기존 `bmad-*` 대신 **`bmadx-*`** 이름을 사용합니다.

예:

- `bmadx-sm`
- `bmadx-pm`
- `bmadx-po`
- `bmadx-dev`
- `bmadx-qa`

즉, 기존 프로젝트에 이미 `bmad-dev`, `bmad-sm` 등이 있어도 가능한 한 건드리지 않는 방향입니다.

---

## 현재 프로젝트가 Git 저장소가 아니어도 되나

됩니다.

이 버전은 Git 저장소 여부에만 의존하지 않고, **현재 위치와 `tools/bmad-codex` 경로 또는 flat repo 루트 구조**를 기준으로 동작하도록 설계되어 있습니다.

다만 Git 저장소이면 루트 추적과 변경 관리가 더 쉬워집니다.

---

## BMAD가 아직 설치되지 않은 프로젝트에서도 되나

가능하게 설계했지만, 가장 안정적인 방식은 **BMAD가 이미 설치된 프로젝트**에서 사용하는 것입니다.

이미 아래가 있으면 가장 좋습니다.

- `_bmad/`
- `_bmad-output/`
- planning artifacts
- `sprint-status.yaml`

없을 경우 bootstrap 단계에서 가능한 범위 내에서 상태 파일 초기화를 시도합니다.

---

## gate 기준

이 저장소는 “말로 완료”를 인정하지 않습니다.

완료 기준은 다음과 같습니다.

- Story 단계: story review gate 통과
- DEV 단계: dev gate 통과
- QA 단계: qa gate 통과

즉, LLM이 “완료했다”고 말해도 실제 gate script가 실패하면 완료로 처리하지 않습니다.

---

## 트러블슈팅

### 1. `bootstrap.sh`가 없다고 나온다

저장소 구조가 잘못 들어간 경우입니다.

정상 경로는 아래여야 합니다.

```text
tools/bmad-codex/bootstrap.sh
```

만약 아래처럼 한 겹 더 들어가 있으면 잘못 clone/압축 해제한 것입니다.

```text
tools/bmad-codex/tools/bmad-codex/bootstrap.sh
```

이 경우 저장소 루트를 평탄화하거나, 패키지 내부 파일을 한 단계 위로 올려야 합니다.

### 2. Windows에서 bash 오류가 난다

PowerShell에서 직접 `.sh`를 돌리지 말고 아래를 사용하세요.

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\bmad-codex\bootstrap.ps1
powershell -ExecutionPolicy Bypass -File .\tools\bmad-codex\run.ps1
```

이 스크립트는 WSL로 위임합니다.

### 3. WSL이 없다

PowerShell에서 설치:

```powershell
wsl --install
```

### 4. Codex 명령을 찾지 못한다

Codex CLI가 현재 셸 또는 WSL 안에 설치되어 있어야 합니다.

WSL 안에서 `codex --help` 가 되는지 먼저 확인하세요.

### 5. `sprint-status.yaml`을 찾지 못한다

다음을 먼저 확인하세요.

- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `.bmad-ephemeral/sprint-status.yaml`

없으면 bootstrap이 planning artifacts 기반 초기화를 시도합니다.

### 6. 기존 `.codex` 설정을 덮어쓸까 걱정된다

이 저장소는 가능한 한 기존 설정을 보존하는 방향으로 설치됩니다.
다만 충돌 가능성이 있으면 먼저 `.codex`, `.agents`를 백업하는 것이 좋습니다.

---

## 권장 운영 방식

가장 안정적인 흐름은 이렇습니다.

1. 실제 프로젝트에 BMAD 설치
2. planning / sprint-status 생성
3. 이 저장소를 `tools/bmad-codex` 로 clone
4. bootstrap 실행
5. run 실행
6. 이후에는 상태 파일 기준 자동 진행

---

## 제거

```bash
bash tools/bmad-codex/uninstall.sh
```

Windows PowerShell에서는 WSL 또는 Git Bash로 실행하는 것이 안전합니다.

---

## 주의

이 저장소는 BMAD를 완전히 대체하는 것이 아니라, **BMAD의 agent/workflow를 Codex 실행 환경에 맞게 연결하는 어댑터**입니다.

즉,

- BMAD persona를 최대한 참고하고
- BMAD 상태 파일을 기준으로 진행하고
- Codex가 실제 작업과 실제 검증을 하도록 강제하는 역할

을 담당합니다.
