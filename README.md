# Linux System Monitor

[![CI](https://github.com/jiyoon99/linux-system-monitor/actions/workflows/ci.yml/badge.svg)](https://github.com/jiyoon99/linux-system-monitor/actions/workflows/ci.yml)

FastAPI, Docker, nginx, Ollama를 활용한 Linux 서버 실시간 모니터링 웹 대시보드입니다.

## 주요 기능

- CPU, RAM, Disk, Network 실시간 모니터링
- Chart.js 기반 CPU/RAM/Network history 그래프
- Docker 데몬 상태와 컨테이너 상태 표시
- Server Bot 자동 점검
  - 중지된 컨테이너 감지
  - CPU/RAM/Disk 임계치 경고
  - `WARN`/`FAIL` 로그 출력
- Ollama 로컬 AI 서버 연동
  - Ollama 연결 상태 확인
  - 설치 모델 목록 표시
  - 현재 시스템 상태 AI 분석
- 2초 간격 자동 새로고침
- 다크 테마 hacker/developer 스타일 UI
- 모바일 반응형 레이아웃
- 웹 대시보드와 CLI 동시 지원

## 기술 스택

- Python 3.12
- FastAPI
- Jinja2
- psutil
- Chart.js
- Docker Compose
- nginx reverse proxy
- Ollama local LLM API
- HTML, CSS, JavaScript

## 아키텍처

```text
Browser
  -> nginx reverse proxy (:8080)
  -> FastAPI app (:18000, host network)
  -> Linux host metrics (/proc, /sys)
  -> Docker Engine (/var/run/docker.sock)
  -> Ollama API (localhost:11434)
```

FastAPI 앱과 nginx는 Docker Compose에서 `network_mode: host`로 실행됩니다. FastAPI 앱은 Portainer의 8000 포트와 충돌하지 않도록 호스트의 `18000` 포트에 바인딩됩니다.

nginx는 별도 컨테이너로 실행되며 `127.0.0.1:18000`으로 FastAPI 앱에 요청을 전달합니다. 브라우저는 nginx가 공개한 `http://127.0.0.1:8080`으로 접속합니다. Ollama는 호스트 네트워크의 `http://localhost:11434`로 접근합니다.

## 실행 방법

### Docker Compose

```bash
docker compose up -d --build
```

브라우저에서 접속:

```bash
http://127.0.0.1:8080
```

상태 확인:

```bash
docker compose ps
curl http://127.0.0.1:8080/healthz
```

### 로컬 개발

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
linux-dashboard-web
```

브라우저에서 접속:

```bash
http://127.0.0.1:8000
```

CLI 실행:

```bash
linux-dashboard
linux-dashboard --once --top 10
```

## Docker Compose 설정

핵심 설정:

```yaml
services:
  app:
    network_mode: host
    environment:
      OLLAMA_BASE_URL: http://localhost:11434
      OLLAMA_MODEL: qwen2.5-coder:14b
      OLLAMA_ANALYZE_TIMEOUT: "300"
      OLLAMA_ANALYZE_NUM_PREDICT: "220"
    command: ["--host", "0.0.0.0", "--port", "18000"]
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/host/root:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro

  nginx:
    network_mode: host
```

## Ollama 연동

Ollama 설치:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Ollama 실행:

```bash
ollama serve
```

모델 다운로드:

```bash
ollama run qwen2.5-coder:14b
```

API 확인:

```bash
curl http://localhost:11434/api/tags
```

대시보드는 `/api/ollama/status`로 연결 상태를 확인하고, `/api/ollama/analyze`에서 현재 CPU/RAM/Disk/Docker 상태를 Ollama에 전달해 짧은 분석 결과를 받습니다.

## API 엔드포인트

| Method | Endpoint | 설명 |
| --- | --- | --- |
| `GET` | `/` | 메인 대시보드 |
| `GET` | `/healthz` | 서버 상태 확인 |
| `GET` | `/api/snapshot` | 단일 시점 시스템 스냅샷 |
| `GET` | `/api/metrics` | 현재 metrics와 history |
| `GET` | `/api/alerts` | Server Bot 경고 |
| `GET` | `/api/ollama/status` | Ollama 연결 상태 |
| `GET` | `/api/ollama/models` | Ollama 모델 목록 |
| `POST` | `/api/ollama/analyze` | AI 시스템 분석 |

AI 분석 요청:

```bash
curl -X POST http://127.0.0.1:8080/api/ollama/analyze \
  -H 'Content-Type: application/json' \
  -d '{}'
```

## 검증

```bash
python3 -m compileall src
docker compose config
docker compose up -d --build
curl http://127.0.0.1:8080/api/ollama/status
```

## Troubleshooting

### Ollama server offline

```bash
curl http://localhost:11434/api/tags
ollama serve
```

systemd 사용 시:

```bash
sudo systemctl start ollama
sudo systemctl status ollama
```

### model not found

```bash
ollama run qwen2.5-coder:14b
```

### connection refused

호스트에서 Ollama API가 응답하는지 먼저 확인합니다.

```bash
curl http://localhost:11434/api/tags
```

host network를 사용할 수 없는 환경에서는 `OLLAMA_BASE_URL`을 접근 가능한 호스트 IP로 변경하고 nginx upstream도 함께 조정합니다.

```yaml
environment:
  OLLAMA_BASE_URL: http://172.17.0.1:11434
```

### AI 분석이 느림

14B 모델은 CPU 환경에서 느릴 수 있습니다. 응답 길이를 줄이거나 더 작은 모델을 사용합니다.

```yaml
environment:
  OLLAMA_ANALYZE_NUM_PREDICT: "120"
  OLLAMA_MODEL: qwen2.5-coder:7b
```

### nginx 502 또는 504

```bash
docker compose logs nginx
docker compose logs app
cat nginx/default.conf
```

현재 nginx upstream은 `127.0.0.1:18000`입니다.

### Docker 상태가 degraded

Docker socket 마운트와 권한을 확인합니다.

```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro
```

## 향후 개선 계획

- AI 분석 결과 캐싱
- 최근 분석 히스토리 저장
- Server Bot alert acknowledge 기능
- 컨테이너별 CPU/RAM 상세 모니터링
- Prometheus/Grafana export endpoint
- WebSocket 기반 push 업데이트
- GitHub Actions 테스트 범위 확대
- 운영 서버 배포 예제 추가
