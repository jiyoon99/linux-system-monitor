# Linux System Monitor

[![CI](https://github.com/jiyoon99/linux-system-monitor/actions/workflows/ci.yml/badge.svg)](https://github.com/jiyoon99/linux-system-monitor/actions/workflows/ci.yml)

FastAPI, Docker, nginx, Chart.js, Ollama를 조합해 만든 Linux 서버 실시간 모니터링 대시보드입니다. 단순 지표 표시를 넘어서 Docker 런타임 상태, 자동 점검 봇, 로컬 LLM 기반 시스템 분석까지 한 화면에서 확인할 수 있도록 구성했습니다.

![Dashboard screenshot](docs/screenshots/dashboard.png)

## What I Built / 만든 것

호스트의 CPU, 메모리, 디스크, 네트워크와 Docker 런타임 상태를 수집해 웹과 CLI에서 확인할 수 있는 모니터링 도구를 만들었습니다. 수집된 수치를 그대로 나열하는 데서 끝내지 않고 Server Bot이 임계치와 중지된 컨테이너를 검사해 `OK`, `WARN`, `FAIL` 상태로 요약하며, 필요할 때 Ollama가 현재 상태를 한국어로 분석합니다.

## Main Features / 주요 기능

- 실시간 CPU, RAM, Disk, Network 모니터링
- Chart.js 기반 CPU/RAM/Network 히스토리 그래프
- Docker daemon, container, image 상태 표시
- Server Bot 자동 점검
  - CPU/RAM/Disk 임계치 감시
  - 중지된 컨테이너 감지
  - `OK`/`WARN`/`FAIL` 상태 리포트
- Ollama 로컬 AI 서버 연동
  - Ollama 연결 상태 확인
  - 설치된 모델 목록 표시
  - 현재 시스템 상태 AI 분석
- nginx reverse proxy와 Docker Compose 기반 실행
- 다크 테마 반응형 UI
- 웹 대시보드와 CLI 동시 지원

## Development / 개발 방식

- Linux metrics 수집을 별도 모듈로 분리해 CLI와 FastAPI가 같은 snapshot을 사용합니다.
- 컨테이너 실행 시 호스트의 `/proc`, `/sys`, root filesystem을 읽기 전용으로 마운트합니다.
- Docker 상태는 `/var/run/docker.sock`을 읽기 전용으로 연결해 daemon, container, image 정보를 조회합니다.
- 현재값과 history를 분리해 API가 Chart.js 그래프에 필요한 시계열을 제공합니다.
- Server Bot은 수집 계층과 분리된 규칙으로 CPU, RAM, disk 임계치와 중지 컨테이너를 판정합니다.
- Ollama 상태 확인과 분석 요청을 별도 endpoint로 분리해 AI 서버가 꺼져 있어도 기본 모니터링은 계속 동작합니다.
- nginx가 외부 `8080` 요청을 받고 FastAPI는 내부 `18000`에서 동작하도록 실행 경계를 나눴습니다.

## Tech Stack / 기술 스택

| Area | Stack |
| --- | --- |
| Backend | Python 3.12, FastAPI, psutil, Jinja2 |
| Frontend | HTML, CSS, JavaScript, Chart.js |
| Runtime | Docker, Docker Compose, nginx |
| AI integration | Ollama local LLM API |
| Monitoring | `/proc`, `/sys`, Docker socket |

## Architecture / 아키텍처

```text
Browser
  -> nginx reverse proxy (:8080)
  -> FastAPI app (:18000, host network)
  -> Linux host metrics (/proc, /sys, /)
  -> Docker Engine (/var/run/docker.sock)
  -> Ollama API (localhost:11434)
```

FastAPI 앱과 nginx는 `network_mode: host`로 실행됩니다. Portainer가 `8000` 포트를 사용 중인 환경에서도 충돌하지 않도록 FastAPI 앱은 `18000` 포트에 바인딩하고, nginx는 외부 접속용 `8080` 포트를 사용합니다.

## Current Runtime / 현재 실행 환경

현재 기본 실행 주소:

```text
http://127.0.0.1:8080
```

기본 포트:

| Service | Port | Purpose |
| --- | ---: | --- |
| nginx | 8080 | Browser entrypoint |
| FastAPI app | 18000 | Internal dashboard API |
| Ollama | 11434 | Local LLM API |

## Quick Start / 빠른 시작

```bash
docker compose up -d --build
```

상태 확인:

```bash
docker compose ps
curl http://127.0.0.1:8080/healthz
curl http://127.0.0.1:8080/api/metrics
```

브라우저에서 접속:

```text
http://127.0.0.1:8080
```

## Local Development / 로컬 개발

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
linux-dashboard-web
```

로컬 개발 서버:

```text
http://127.0.0.1:8000
```

CLI:

```bash
linux-dashboard
linux-dashboard --once --top 10
```

## Docker Compose Notes / Docker Compose 참고사항

핵심 설정:

```yaml
services:
  app:
    network_mode: host
    command: ["--host", "0.0.0.0", "--port", "18000"]
    environment:
      OLLAMA_BASE_URL: http://localhost:11434
      OLLAMA_MODEL: qwen2.5-coder:14b
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/host/root:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro

  nginx:
    network_mode: host
```

nginx upstream:

```nginx
upstream linux_dashboard_app {
    server 127.0.0.1:18000;
}
```

## Ollama Integration / Ollama 연동

Ollama API 확인:

```bash
curl http://localhost:11434/api/tags
```

모델 다운로드:

```bash
ollama run qwen2.5-coder:14b
```

대시보드는 `/api/ollama/status`로 서버와 모델 상태를 확인하고, `/api/ollama/analyze`에서 현재 CPU/RAM/Disk/Docker 상태를 Ollama에 전달해 짧은 한국어 분석 결과를 받습니다.

## API / API 안내

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/` | Dashboard UI |
| `GET` | `/healthz` | Health check |
| `GET` | `/api/snapshot` | Single system snapshot |
| `GET` | `/api/metrics` | Current metrics with history |
| `GET` | `/api/alerts` | Server Bot report |
| `GET` | `/api/ollama/status` | Ollama connection status |
| `GET` | `/api/ollama/models` | Installed Ollama models |
| `POST` | `/api/ollama/analyze` | AI system analysis |

AI 분석 요청:

```bash
curl -X POST http://127.0.0.1:8080/api/ollama/analyze \
  -H 'Content-Type: application/json' \
  -d '{}'
```

## Validation / 검증

```bash
python3 -m compileall src
docker compose config
docker compose up -d --build
curl http://127.0.0.1:8080/healthz
curl http://127.0.0.1:8080/api/ollama/status
```

Expected healthy signals:

- `/healthz` returns `{"status":"ok"}`
- Docker Compose shows `linux-dashboard-app` as healthy
- `/api/ollama/status` reports `server_status: running`
- `default_model_available` is `true` when `qwen2.5-coder:14b` is installed

## Troubleshooting / 문제 해결

### Port already in use / 포트가 이미 사용 중인 경우

FastAPI는 `18000`, nginx는 `8080`을 사용합니다. 충돌이 있으면 `docker-compose.yml`과 `nginx/default.conf`를 함께 수정해야 합니다.

### Ollama server offline / Ollama 서버가 꺼진 경우

```bash
curl http://localhost:11434/api/tags
ollama serve
```

systemd 환경:

```bash
sudo systemctl start ollama
sudo systemctl status ollama
```

### Model not found / 모델을 찾을 수 없는 경우

```bash
ollama run qwen2.5-coder:14b
```

### Docker status degraded / Docker 상태가 저하된 경우

Docker socket 마운트와 권한을 확인합니다.

```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro
```

중지된 테스트 컨테이너가 많으면 Server Bot이 `WARN`을 표시합니다.

```bash
docker ps -a --filter status=exited
docker rm <container_id>
```

## License / 라이선스

MIT License. 자세한 내용은 [LICENSE](LICENSE)를 참고하세요.
