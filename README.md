# Linux Dashboard

Python 기반 Linux 시스템 모니터 CLI입니다. CPU, 메모리, 디스크, 네트워크, 프로세스 정보를 터미널 UI로 표시합니다.

## 로컬 실행

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
linux-dashboard
```

옵션:

```bash
linux-dashboard --interval 2 --top 10
linux-dashboard --once
```

## Docker 실행

이미지 빌드:

```bash
docker build -t linux-dashboard .
```

컨테이너 내부 상태만 보기:

```bash
docker run --rm -it linux-dashboard
```

호스트 Linux 상태를 더 정확히 보려면 Docker Compose를 사용합니다.

```bash
docker compose up --build
```

Compose 구성은 호스트의 `/proc`, `/sys`, `/`를 읽기 전용으로 마운트합니다. 컨테이너 환경과 권한에 따라 일부 값은 제한될 수 있습니다.

## 개발

```bash
python3 -m compileall src
```

