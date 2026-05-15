# Linux System Monitor

Python 기반 Linux 시스템 모니터입니다. 브라우저 웹 대시보드와 터미널 CLI를 모두 제공합니다.

## 웹 대시보드 실행

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
linux-dashboard-web
```

브라우저에서 엽니다.

```bash
http://127.0.0.1:8000
```

웹 서버 옵션:

```bash
linux-dashboard-web --host 0.0.0.0 --port 8000
```

## CLI 실행

터미널 UI로 실행:

```bash
linux-dashboard
```

단발 출력:

```bash
linux-dashboard --once --top 10
```

## Docker 실행

```bash
docker build -t linux-dashboard .
docker run --rm -it --network host linux-dashboard
```

호스트 Linux 상태를 더 정확히 보려면 Docker Compose를 사용합니다.

```bash
docker compose up --build
```

Compose 실행 후 브라우저에서 엽니다.

```bash
http://127.0.0.1:8000
```

Compose 구성은 호스트의 `/proc`, `/sys`, `/`를 읽기 전용으로 마운트합니다. 컨테이너 환경과 권한에 따라 일부 값은 제한될 수 있습니다.

## 개발

```bash
python3 -m compileall src
```

Linux Mint GNOME 개발 환경 점검:

```bash
./check-system.sh
```
