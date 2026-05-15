# Linux System Monitor

FastAPI 기반 Linux 시스템 모니터링 웹 대시보드입니다. CPU, RAM, Disk, Network, Docker 상태를 실시간으로 시각화하고, 로컬 Ollama 모델을 사용해 현재 서버 상태를 AI로 요약 분석합니다.

다크 테마의 hacker/developer 스타일 UI, nginx reverse proxy, Docker Compose 실행 환경, CLI 모니터링 도구를 함께 제공합니다.

## 주요 기능

- CPU, RAM, Disk, Network 실시간 상태 카드
- Chart.js 기반 CPU/RAM/Network history 그래프
- 디스크 사용률 게이지와 마운트별 상세 표
- Docker 데몬 상태, 컨테이너 수, 이미지 수 표시
- Server Bot 자동 점검
  - 중지된 Docker 컨테이너 감지
  - CPU/RAM/Disk 임계치 경고
  - `WARN`/`FAIL` 로그 출력
- Local AI Server 연동
  - Ollama API 연결 상태 확인
  - 설치된 모델 목록 표시
  - `qwen2.5-coder:14b` 기반 시스템 상태 분석
- 2초 간격 자동 새로고침
- 모바일 반응형 대시보드
- FastAPI 웹 서버와 터미널 CLI 동시 지원

## 기술 스택

- Python 3.12
- FastAPI
- Jinja2
- psutil
- Chart.js
- Docker / Docker Compose
- nginx reverse proxy
- Ollama local LLM API
- HTML, CSS, JavaScript

## 아키텍처

```text
Browser
  |
  | http://127.0.0.1:8080
  v
nginx reverse proxy
  |
  | proxy_pass http://host.docker.internal:8000
  v
FastAPI app container
  |
  | reads /proc, /sys, Docker socket
  v
Linux host metrics + Docker Engine
  |
  | OLLAMA_BASE_URL=http://localhost:11434
  v
Ollama local AI server
```

Docker Compose에서 FastAPI 앱은 Linux `host` network로 실행됩니다. 이 구조 덕분에 호스트에서 `127.0.0.1:11434`로 실행 중인 Ollama API에 컨테이너가 직접 접근할 수 있습니다. nginx는 별도 컨테이너로 유지하며 `host.docker.internal:8000`으로 FastAPI 앱에 reverse proxy 합니다.

## 스크린샷

![Linux Dashboard screenshot](docs/screenshots/dashboard.png)

## 실행 방법

### 1. Ollama 준비

Ollama 설치:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Ollama 서버 실행:

```bash
ollama serve
```

systemd 환경:

```bash
sudo systemctl enable --now ollama
sudo systemctl status ollama
```

분석 모델 다운로드:

```bash
ollama run qwen2.5-coder:14b
```

Ollama API 확인:

```bash
curl http://localhost:11434/api/tags
```

### 2. Docker Compose 실행

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
curl http://127.0.0.1:8080/api/ollama/status
```

### 3. 로컬 개발 실행

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

## 주요 설정

`docker-compose.yml`의 app 서비스는 아래 Ollama 설정을 사용합니다.

```yaml
network_mode: host
environment:
  OLLAMA_BASE_URL: http://localhost:11434
  OLLAMA_MODEL: qwen2.5-coder:14b
  OLLAMA_ANALYZE_TIMEOUT: "300"
  OLLAMA_ANALYZE_NUM_PREDICT: "220"
```

Server Bot 임계치는 환경변수로 조정할 수 있습니다.

```bash
BOT_CPU_WARN=80
BOT_CPU_FAIL=95
BOT_RAM_WARN=80
BOT_RAM_FAIL=95
BOT_DISK_WARN=85
BOT_DISK_FAIL=95
```

## API 엔드포인트

| Method | Endpoint | 설명 |
| --- | --- | --- |
| `GET` | `/` | 메인 대시보드 |
| `GET` | `/healthz` | FastAPI health check |
| `GET` | `/api/snapshot` | 단일 시점 시스템 스냅샷 |
| `GET` | `/api/metrics` | 현재 metrics와 history 샘플 |
| `GET` | `/api/alerts` | Server Bot 경고 상태 |
| `GET` | `/api/ollama/status` | Ollama 연결 상태와 기본 모델 상태 |
| `GET` | `/api/ollama/models` | Ollama 설치 모델 목록 |
| `POST` | `/api/ollama/analyze` | 현재 시스템 상태 AI 분석 |

AI 분석 API 예시:

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

호스트에서 Ollama가 실행 중인지 확인합니다.

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

기본 분석 모델을 내려받습니다.

```bash
ollama run qwen2.5-coder:14b
```

### connection refused

호스트에서 먼저 확인합니다.

```bash
curl http://localhost:11434/api/tags
```

이 프로젝트의 Compose 구성은 app 컨테이너를 host network로 실행하므로, 호스트에서 위 명령이 성공하면 app도 `http://localhost:11434`로 접근할 수 있습니다.

host network를 사용할 수 없는 환경에서는 `OLLAMA_BASE_URL`을 접근 가능한 IP로 변경합니다.

```yaml
environment:
  OLLAMA_BASE_URL: http://172.17.0.1:11434
```

### AI 분석이 느림

`qwen2.5-coder:14b`는 CPU 환경에서 느릴 수 있습니다. 응답 길이를 줄이거나 더 작은 모델을 사용합니다.

```yaml
environment:
  OLLAMA_ANALYZE_NUM_PREDICT: "120"
  OLLAMA_MODEL: qwen2.5-coder:7b
```

### nginx 502 또는 504

nginx upstream과 timeout 설정을 확인합니다.

```bash
cat nginx/default.conf
docker compose logs nginx
docker compose logs app
```

현재 nginx는 `host.docker.internal:8000`으로 FastAPI 앱에 연결합니다.

### Docker 상태가 degraded

Docker socket 마운트와 권한을 확인합니다.

```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro
```

소켓 접근 권한이 없으면 Docker 섹션만 degraded로 표시되고 CPU/RAM/Disk metrics는 계속 갱신됩니다.

## 향후 개선 계획

- AI 분석 결과 캐싱과 최근 분석 히스토리 저장
- Server Bot alert acknowledge 기능
- Docker 컨테이너별 CPU/RAM 상세 모니터링
- Prometheus/Grafana export endpoint 추가
- 사용자 설정 UI에서 임계치 조정
- WebSocket 기반 push 업데이트
- GitHub Actions 기반 lint/test/build 자동화
- 실제 운영 서버 배포 예제 추가
