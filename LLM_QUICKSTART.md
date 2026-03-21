# LLM Quickstart

이 저장소는 GitHub에서는 패키지 루트가 평탄화된 구조입니다. 실제 프로젝트에는 보통 `tools/bmad-codex`로 clone 해서 사용합니다.

프로젝트 루트라면 아래 순서대로 실행하세요.

```bash
mkdir -p tools
git clone <THIS_REPO_URL> tools/bmad-codex
bash tools/bmad-codex/bootstrap.sh
```

설치가 끝난 뒤 오케스트레이터만 다시 돌리고 싶다면:

```bash
python3 tools/bmad-codex/orchestrator/main.py
```

이 저장소 자체를 루트에서 직접 테스트 중이라면 아래 명령도 사용할 수 있습니다.

```bash
bash ./bootstrap.sh
python3 ./orchestrator/main.py
```
