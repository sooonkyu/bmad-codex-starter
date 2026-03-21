# BMAD Codex Starter v3

BMAD 방식의 `SM -> PM/PO -> DEV -> QA` 자동화 루프를 `Codex`, gate script, `sprint-status.yaml` 기반 상태 추적으로 실행하기 위한 스타터 킷입니다.

이 저장소는 GitHub에서 볼 때 **repo 루트가 곧 패키지 루트**인 평탄 구조입니다. 실제 프로젝트에 붙일 때는 보통 이 저장소를 `tools/bmad-codex`로 clone 해서 사용합니다.

## Repo Layout

```text
repo-root/
  README.md
  LLM_QUICKSTART.md
  bootstrap.sh
  install.sh
  uninstall.sh
  orchestrator/
    main.py
  templates/
    ...
```

## 가장 빠른 사용법

프로젝트 루트에서 아래처럼 실행하면 됩니다.

```bash
mkdir -p tools
git clone <THIS_REPO_URL> tools/bmad-codex
bash tools/bmad-codex/bootstrap.sh
```

스크립트는 아래 두 배치를 모두 지원합니다.

- 이 저장소를 프로젝트 안 `tools/bmad-codex`로 clone 한 경우
- 이 저장소 자체를 루트에서 직접 실행하며 테스트하는 경우

## LLM에게 주는 짧은 지시문

```text
현재 디렉터리는 프로젝트 루트다.
1. tools/bmad-codex 가 없으면 <THIS_REPO_URL> 을 tools/bmad-codex 로 clone 해라.
2. tools/bmad-codex/README.md 를 읽고 그 지시를 따라라.
3. bash tools/bmad-codex/bootstrap.sh 를 실행해라.
4. 실패하면 .bmadx/state/*.json, sprint-status.yaml, gate 로그를 확인해 고쳐라.
5. 필요하면 python3 tools/bmad-codex/orchestrator/main.py 를 다시 실행해라.
```

## bootstrap.sh 가 하는 일

`bootstrap.sh`는 순서대로 아래 작업을 시도합니다.

1. 프로젝트 루트를 판별합니다.
2. `_bmad/` 존재 여부를 확인합니다.
3. 없으면 `npx bmad-method install`을 시도합니다.
4. `install.sh`로 Codex/BMAD 연결 파일을 배치합니다.
5. BMAD agent/workflow를 인덱싱합니다.
6. 기술 스택과 실행 명령을 탐지해 `.bmadx/state/runtime-manifest.json`을 생성합니다.
7. `sprint-status.yaml`을 찾거나 planning artifacts를 기반으로 부트스트랩합니다.
8. `codex` CLI가 준비되어 있으면 오케스트레이터를 실행합니다.

## 추천 프로젝트 배치

이 저장소 자체는 평탄하지만, 실제 프로젝트 안에서는 아래처럼 두는 것을 권장합니다.

```text
my-project/
  _bmad/
  _bmad-output/
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

설치가 끝나면 프로젝트 루트에는 보통 아래 파일들이 생깁니다.

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
```

## 자주 쓰는 명령

프로젝트에 설치한 뒤:

```bash
bash tools/bmad-codex/bootstrap.sh
python3 tools/bmad-codex/orchestrator/main.py
python3 tools/bmad-codex/orchestrator/main.py --story 2.1
BMADX_AUTO_RUN=0 bash tools/bmad-codex/bootstrap.sh
```

이 저장소 루트에서 직접 테스트할 때:

```bash
bash ./bootstrap.sh
python3 ./orchestrator/main.py
python3 ./orchestrator/main.py --story 2.1
BMADX_AUTO_RUN=0 bash ./bootstrap.sh
```

## 상태 기반 자동 진행

오케스트레이터는 `sprint-status.yaml`을 읽고 다음 단계를 정합니다.

- `backlog`: SM이 story 생성 후 PM/PO 검토
- `drafted`, `ready-for-dev`: DEV 구현
- `in-progress`: DEV 계속 진행
- `review`: QA 검증
- `done`: 다음 스토리로 이동
- 모든 스토리가 끝난 epic에 retrospective가 남아 있으면 retrospective 처리

`sprint-status.yaml`은 아래 우선순위로 찾습니다.

1. `.bmad-ephemeral/sprint-status.yaml`
2. `_bmad-output/implementation-artifacts/sprint-status.yaml`
3. `docs/sprint-status.yaml`
4. 프로젝트 전체 검색

## 프로젝트별 명령 고정

자동 탐지 대신 명령을 명시하고 싶다면 아래 파일을 둘 수 있습니다.

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

## 주의

- `codex` CLI 로그인과 인증 자체는 자동화하지 않습니다.
- `_bmad/`가 없고 `npx bmad-method install`이 대화형 선택을 요구하면 수동 개입이 필요할 수 있습니다.
- planning artifacts가 없으면 story 부트스트랩은 제한됩니다.
- 외부 서비스나 비밀값이 필요한 프로젝트는 `.bmadx/project-contract.json` 또는 `.env` 준비가 필요할 수 있습니다.
