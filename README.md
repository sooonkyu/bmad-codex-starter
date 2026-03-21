# BMAD Codex Starter v3

BMAD 방식의 `SM -> PM/PO -> DEV -> QA` 자동화 루프를 **Codex + 외부 gate script + BMAD 원문 참조 + sprint-status 기반 자동 진행**으로 실행하기 위한 스타터 킷입니다.

이 저장소는 **프로젝트 안에 `tools/bmad-codex`로 넣는 어댑터 패키지**입니다. 사람용 README이면서 동시에 **코딩 LLM이 그대로 따라 하기 좋은 실행 지시서**로 작성되어 있습니다.

BMAD 공식 문서는 구현 단계에서 `bmad-sprint-planning`이 `sprint-status.yaml`을 만들고, 이후 `bmad-create-story -> bmad-dev-story -> bmad-code-review` 순서로 각 스토리를 새 채팅에서 반복하라고 설명합니다. 또 산출물 구조 예시로 `_bmad/`, `_bmad-output/planning-artifacts/`, `_bmad-output/implementation-artifacts/sprint-status.yaml`을 제시합니다. 이 패키지는 그 흐름을 Codex 오케스트레이터와 gate script로 자동화하도록 설계했습니다. citeturn652544view0turn652544view5

Codex는 프로젝트 범위 `.codex/config.toml`, `AGENTS.md`, `.agents/skills`, `.codex/agents/*.toml`을 지원하고, `codex exec`와 `resume`으로 세션을 이어갈 수 있습니다. 이 패키지는 그 구조를 그대로 사용합니다. citeturn652544view1turn652544view2turn652544view3

## 이 버전에서 추가된 것

- `bootstrap.sh` 추가: 설치 + 환경 탐지 + `sprint-status.yaml` 부트스트랩 + 자동 실행까지 한 번에 처리
- `bootstrap_sprint_status.py` 추가: `sprint-status.yaml`이 없으면 planning artifacts에서 스토리 키를 추출해 생성
- README를 **LLM 친화적 설치/실행 지시서**로 재작성
- 프로젝트 루트에서 “repo 주소 README 읽고 설치부터 실행까지 모두 세팅해”라고 했을 때 그대로 따라 하기 쉬운 단계와 명령 제공

## 가장 중요한 사용 방식

프로젝트 루트에서 코딩 LLM에게 아래처럼 지시하면 됩니다.

```text
프로젝트 루트에서 다음을 수행해.
1. <THIS_REPO_URL> 을 tools/bmad-codex 로 clone 해.
2. tools/bmad-codex/README.md 를 읽고 그 지시를 그대로 따라.
3. 가능하면 bash tools/bmad-codex/bootstrap.sh 로 설치부터 실행까지 끝내.
4. 실패하면 중간 산출물(.bmadx/state/*.json, sprint-status.yaml, gate log)을 확인해 수정하고 다시 진행해.
```

가장 단순한 실제 명령은 이것입니다.

```bash
# 프로젝트 루트에서
mkdir -p tools
git clone <THIS_REPO_URL> tools/bmad-codex
bash tools/bmad-codex/bootstrap.sh
```

`bootstrap.sh`는 다음을 시도합니다.

1. 프로젝트 루트 확인
2. `_bmad/` 존재 여부 확인
3. 없으면 `npx bmad-method install` 시도
4. 이 패키지 설치 (`install.sh`)
5. BMAD agent/workflow 인덱싱
6. 기술 스택 및 명령 탐지 (`runtime-manifest.json` 생성)
7. `sprint-status.yaml` 탐색 또는 planning artifacts 기반 생성
8. Codex CLI가 있으면 오케스트레이터 자동 실행

## 한계와 전제

- **Codex CLI 로그인/인증 자체는 자동화하지 않습니다.** `codex` 명령이 PATH에 있고 이미 사용 가능한 상태여야 실행 단계가 완전히 자동화됩니다. Codex CLI는 프로젝트 범위 설정과 비대화형 실행을 지원하지만, 인증은 별도 선행이 필요합니다. citeturn652544view1
- `_bmad/`가 없고 `npx bmad-method install`이 대화형 선택을 요구하는 경우, BMAD 설치 단계는 일부 수동 개입이 필요할 수 있습니다.
- planning artifacts 자체가 없다면 `sprint-status.yaml`도 자동 생성할 수 없습니다.

## 추천 프로젝트 배치

```text
my-project/
  _bmad/
  _bmad-output/
  tools/
    bmad-codex/
```

설치 후에는 아래가 추가됩니다.

```text
my-project/
  .agents/
    skills/
      bmad-sm -> tools/bmad-codex/templates/skills/bmad-sm
      bmad-pm -> tools/bmad-codex/templates/skills/bmad-pm
      bmad-po -> tools/bmad-codex/templates/skills/bmad-po
      bmad-dev -> tools/bmad-codex/templates/skills/bmad-dev
      bmad-qa -> tools/bmad-codex/templates/skills/bmad-qa
  .codex/
    config.toml
    agents/
      sm.toml
      pm.toml
      po.toml
      dev.toml
      qa.toml
  AGENTS.override.md
  .bmadx/
    state/
      runtime-manifest.json
      role-map.json
      sessions.json
      planner.json
      sprint-status.path
      last-gate-story.log
      last-gate-dev.log
      last-gate-qa.log
    reviews/
    runs/
  scripts/
    bmadx/
      index_bmad.py
      discover_env.py
      bootstrap_sprint_status.py
      sprint_status.py
      gate.py
    gates/
      discover_env_gate.sh
      story_review_gate.sh
      dev_gate.sh
      qa_gate.sh
  tools/
    bmad-codex/
      bootstrap.sh
      install.sh
      uninstall.sh
      orchestrator/
        main.py
      templates/
        ...
```

## 사람/LLM 공통 설치 순서

```bash
# 1) 프로젝트 루트로 이동
cd my-project

# 2) 이 저장소 추가
mkdir -p tools
git clone <THIS_REPO_URL> tools/bmad-codex

# 3) 한 번에 설치 + 부트스트랩 + 실행
bash tools/bmad-codex/bootstrap.sh
```

오케스트레이터만 다시 돌리고 싶으면:

```bash
python3 tools/bmad-codex/orchestrator/main.py
```

특정 스토리만 강제로 돌리고 싶으면:

```bash
python3 tools/bmad-codex/orchestrator/main.py --story 2.1
```

자동 실행 없이 세팅만 하고 싶으면:

```bash
BMADX_AUTO_RUN=0 bash tools/bmad-codex/bootstrap.sh
```

## 상태 파일 기반 자동 진행

오케스트레이터는 `sprint-status.yaml`의 story status를 보고 다음 단계를 정합니다.

- `backlog` -> SM이 story 생성 -> PM/PO 검토
- `drafted` / `ready-for-dev` -> DEV 구현
- `in-progress` -> DEV 계속 진행
- `review` -> QA 검증
- `done` -> 다음 스토리 이동
- 모든 스토리가 끝난 epic의 retrospective 항목이 있으면 retrospective 처리

`sprint-status.yaml`은 아래 우선순위로 찾습니다.

1. `.bmad-ephemeral/sprint-status.yaml`
2. `_bmad-output/implementation-artifacts/sprint-status.yaml`
3. `docs/sprint-status.yaml`
4. 프로젝트 내부 검색

BMAD 공식 가이드는 `sprint-status.yaml`을 implementation tracking 파일로 설명하고, 최근 BMAD 관련 이슈에서는 일부 워크플로가 `.bmad-ephemeral` 또는 서로 다른 story path를 참조해 경로 불일치가 보고됐습니다. 그래서 이 패키지는 여러 후보 경로를 읽고, 없으면 planning artifacts를 바탕으로 새로 만들도록 되어 있습니다. citeturn652544view0turn340863search0

## 기술 스택 자동 탐지

`discover_env.py`는 아래 스택을 우선순위 기반으로 탐지합니다.

- Node.js / npm / pnpm / yarn
- Python / uv / poetry / pip
- Java / Maven / Gradle
- Go
- Rust
- PHP / Composer / Laravel

탐지 결과는 `.bmadx/state/runtime-manifest.json`에 저장되고, DEV/QA gate는 이 파일만 보고 실제 명령을 실행합니다.

## 프로젝트별 덮어쓰기

탐지 결과를 명시적으로 고정하고 싶으면 아래 파일을 두세요.

```text
.bmadx/project-contract.json
```

예시:

```json
{
  "commands": {
    "install": "pnpm install --frozen-lockfile",
    "lint": "pnpm lint",
    "typecheck": "pnpm typecheck",
    "test_unit": "pnpm test",
    "test_e2e": "pnpm test:e2e",
    "build": "pnpm build"
  },
  "bootstrap": {
    "services": ["docker compose up -d db redis"],
    "migrations": "pnpm prisma migrate deploy"
  }
}
```

## BMAD agent 원문과 커스터마이징

이 패키지는 `_bmad/` 안의 BMAD agent markdown을 실제로 참조하도록 설계돼 있습니다. 추가로 BMAD는 `_bmad/_config/agents/*.customize.yaml`을 통해 agent 이름, persona, memory, critical actions를 커스터마이징하고 다시 빌드하는 방식을 공식 지원합니다. 그래서 프로젝트별 규칙을 더 강하게 넣고 싶으면 BMAD customize 파일과 이 패키지의 `AGENTS.override.md`를 같이 쓰는 게 좋습니다. citeturn652544view4

## LLM에게 그대로 줄 수 있는 짧은 지시문

```text
현재 디렉터리는 프로젝트 루트다.
1. tools/bmad-codex 가 없으면 <THIS_REPO_URL> 을 tools/bmad-codex 로 clone 해.
2. tools/bmad-codex/README.md 를 읽어라.
3. bash tools/bmad-codex/bootstrap.sh 를 실행해라.
4. bootstrap 이 실패하면 오류 원인을 고치고 다시 실행해라.
5. 설치 후 python3 tools/bmad-codex/orchestrator/main.py 를 실행해라.
6. .bmadx/state/runtime-manifest.json, .bmadx/state/planner.json, sprint-status.yaml, gate 로그를 확인하며 끝까지 진행해라.
```

## 주의

- `codex exec --json` 출력 형식은 CLI 버전에 따라 일부 달라질 수 있어, 필요하면 `orchestrator/main.py`의 JSON event parsing을 현재 버전에 맞게 조정해야 할 수 있습니다.
- BMAD planning artifacts가 없으면 story 부트스트랩이 제한됩니다.
- 외부 서비스, DB seed, 비밀값이 필요한 프로젝트는 `.bmadx/project-contract.json` 또는 `.env` 준비가 필요합니다.
