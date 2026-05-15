# Linux System Monitor

Python 기반 Linux 시스템 모니터입니다. FastAPI + Jinja2 웹 대시보드와 터미널 CLI를 모두 제공합니다.

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

## 화면과 주소

- `http://127.0.0.1:8000/`: 메인 웹 대시보드입니다. 다크 hacker/developer 스타일 UI로 CPU, RAM, Disk, Network 카드와 실시간 그래프, Docker 상태, 디스크 상세, 상위 프로세스를 보여줍니다.
- `http://127.0.0.1:8000/api/metrics`: 대시보드가 2초마다 읽는 JSON 데이터 주소입니다. 현재 스냅샷과 최근 history 샘플을 함께 제공합니다.
- `http://127.0.0.1:8000/api/alerts`: 자동 서버 관리 봇이 평가한 경고 상태, 중지된 Docker 컨테이너 목록, 임계치 정보를 제공합니다.
- `http://127.0.0.1:8000/api/ollama/status`: Ollama API 연결 가능 여부와 기본 분석 모델 상태를 제공합니다.
- `http://127.0.0.1:8000/api/ollama/models`: Ollama에 설치된 모델 목록을 제공합니다.
- `http://127.0.0.1:8000/api/ollama/analyze`: 현재 시스템 metrics를 Ollama에 전달해 AI 분석 결과를 반환합니다.
- `http://127.0.0.1:8000/api/snapshot`: 단일 시점 JSON 스냅샷 주소입니다. 화면 수치가 비어 있으면 먼저 이 주소가 응답하는지 확인할 수 있습니다.
- `http://127.0.0.1:8000/healthz`: 서버 상태 확인 주소입니다. `{"status":"ok"}`가 보이면 웹 서버가 실행 중입니다.
- `http://127.0.0.1:8000/static/...`: 브라우저 화면에 필요한 CSS, JavaScript 정적 파일 주소입니다.

화면 의미:

- CPU 카드는 프로그램 실행과 계산을 담당하는 프로세서 사용률, 부하, 코어 수, 동작 속도를 보여줍니다.
- RAM 카드는 현재 앱과 서비스가 사용하는 메모리, 남은 메모리, 스왑 사용량을 보여줍니다.
- Disk 카드는 파일과 Docker 이미지가 저장되는 디스크의 전체 사용량을 요약합니다. 아래 디스크 상세 표에서 마운트별 사용량을 볼 수 있습니다.
- Network 카드는 서버가 부팅 후 주고받은 데이터와 패킷 수를 보여줍니다.
- 실시간 그래프는 Chart.js를 사용해 CPU 사용률 history, RAM 사용률 history, Network RX/TX 송수신량 history를 표시합니다.
- Disk Usage 패널은 전체 마운트 기준 사용률을 게이지 형태로 표시합니다.
- Docker 상태 섹션은 Docker 명령과 데몬에 접근할 수 있을 때 버전, 컨테이너 수, 이미지 수를 보여줍니다. 접근 권한이 없거나 Docker가 없으면 확인 불가로 표시됩니다.
- Server Bot 섹션은 Docker 컨테이너 상태를 주기적으로 점검하고, 중지된 컨테이너 목록과 CPU/RAM/Disk 임계치 경고를 보여줍니다.
- Local AI Server 섹션은 Ollama 연결 상태, 설치된 모델 목록, `qwen2.5-coder:14b` 준비 여부와 AI 시스템 분석 버튼을 보여줍니다.
- 상위 프로세스 표는 CPU와 메모리를 많이 쓰는 프로세스를 우선 표시합니다.
- 화면은 2초 간격으로 자동 새로고침되며 모바일 화면에서는 카드, 그래프, 표가 반응형으로 재배치됩니다. history 샘플이 충분하지 않거나 Chart.js가 아직 로드되지 않았을 때는 `데이터 수집 중`으로 표시됩니다.

## 자동 서버 관리 봇

FastAPI 앱이 실행되면 Server Bot이 30초마다 시스템 상태를 점검합니다.

- Docker 데몬 접근 가능 여부 확인
- 중지된 Docker 컨테이너 감지
- CPU/RAM/Disk 사용률 임계치 평가
- 문제가 있으면 컨테이너 터미널 로그에 `WARN` 또는 `FAIL` 출력
- 웹 대시보드의 Server Bot 섹션과 `/api/alerts`에서 동일한 상태 확인

기본 임계치:

| 항목 | WARN | FAIL |
| --- | ---: | ---: |
| CPU | 85% | 95% |
| RAM | 85% | 95% |
| Disk | 90% | 97% |

환경변수로 조정할 수 있습니다.

```bash
BOT_CPU_WARN=80
BOT_CPU_FAIL=95
BOT_RAM_WARN=80
BOT_RAM_FAIL=95
BOT_DISK_WARN=85
BOT_DISK_FAIL=95
```

Docker Compose 환경에서는 `docker compose logs -f app`으로 Server Bot의 `WARN`/`FAIL` 로그를 확인할 수 있습니다.

## Ollama 로컬 AI 서버

대시보드는 호스트에서 실행 중인 Ollama API에 연결합니다. Docker Compose 실행 시 앱 컨테이너는 Linux host network로 실행되어 호스트의 `http://localhost:11434` Ollama API에 직접 연결합니다.

- Ollama API 연결 가능 여부
- `http://localhost:11434/api/tags` 기반 모델 목록
- 설치된 모델 목록
- `qwen2.5-coder:14b` 모델 사용 가능 여부
- 현재 CPU/RAM/Disk/Docker 상태 AI 분석

Linux에 Ollama 설치:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Ollama 서버 실행:

```bash
ollama serve
```

systemd 환경에서는 서비스로 실행할 수도 있습니다.

```bash
sudo systemctl enable --now ollama
sudo systemctl status ollama
```

qwen2.5-coder 모델 설치:

```bash
ollama run qwen2.5-coder:14b
```

설치 모델 확인:

```bash
ollama list
```

Ollama API 확인:

```bash
curl http://localhost:11434/api/tags
```

Docker Compose 실행:

```bash
docker compose up --build
```

Compose에서 app 컨테이너는 기본적으로 호스트 Ollama를 아래 주소로 확인합니다.

```yaml
network_mode: host
environment:
  OLLAMA_BASE_URL: http://localhost:11434
  OLLAMA_MODEL: qwen2.5-coder:14b
  OLLAMA_ANALYZE_TIMEOUT: "300"
  OLLAMA_ANALYZE_NUM_PREDICT: "220"
```

로컬에서 `linux-dashboard-web`로 직접 실행할 때는 아래처럼 설정할 수 있습니다.

```bash
OLLAMA_BASE_URL=http://localhost:11434 linux-dashboard-web
```

AI 분석 API 예시:

```bash
curl -X POST http://127.0.0.1:8080/api/ollama/analyze \
  -H 'Content-Type: application/json' \
  -d '{}'
```

문제 해결:

- `Ollama server offline`: `ollama serve` 또는 `sudo systemctl start ollama`로 서버를 실행합니다.
- `connection refused`: 호스트에서 `curl http://localhost:11434/api/tags`가 되는지 먼저 확인합니다. Docker Compose는 app을 host network로 실행하므로 호스트에서 이 명령이 성공하면 app도 같은 주소로 접근할 수 있습니다.
- `model not found`: `ollama run qwen2.5-coder:14b`로 모델을 내려받습니다.
- `timed out`: 14B 모델은 CPU 환경에서 첫 분석이 오래 걸릴 수 있습니다. `OLLAMA_ANALYZE_TIMEOUT` 값을 늘리거나 더 작은 모델을 사용합니다.
- 분석이 너무 느리면 `OLLAMA_ANALYZE_NUM_PREDICT` 값을 낮춰 답변 길이를 줄입니다. 예: `"120"`.
- nginx에서 app으로 연결되지 않으면 `nginx/default.conf`의 upstream이 `host.docker.internal:8000`인지 확인합니다.
- host network를 사용할 수 없는 환경이면 `OLLAMA_BASE_URL`을 접근 가능한 IP로 바꿉니다.

```yaml
environment:
  - OLLAMA_BASE_URL=http://172.17.0.1:11434
```

## 스크린샷

![Linux Dashboard screenshot](docs/screenshots/dashboard.png)

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

nginx reverse proxy를 포함해 실행:

```bash
docker compose up --build
```

Compose 실행 후 브라우저에서 엽니다.

```bash
http://127.0.0.1:8080
```

Docker Compose로 실행할 때는 `http://127.0.0.1:8080/`이 nginx를 거쳐 메인 대시보드로 연결됩니다. FastAPI 앱은 Linux host network에서 `127.0.0.1:8000`으로 실행되며, nginx가 `host.docker.internal:8000` upstream으로 브라우저 요청을 대신 전달합니다.

구성:

- `app`: FastAPI/uvicorn 대시보드 컨테이너
- `nginx`: `host.docker.internal:8000`으로 프록시하는 nginx reverse proxy

Compose 구성은 호스트의 `/proc`, `/sys`, `/`를 읽기 전용으로 마운트합니다. 컨테이너 환경과 권한에 따라 일부 값은 제한될 수 있습니다.
Docker 상태 표시는 `/var/run/docker.sock`을 읽기 전용으로 마운트해 Docker Engine API에서 가져옵니다. 소켓 접근 권한이 없으면 Docker 상태만 `degraded`로 표시되고 나머지 시스템 지표는 계속 갱신됩니다.

FastAPI 앱만 직접 실행:

```bash
docker build -t linux-dashboard .
docker run --rm -p 8000:8000 linux-dashboard
```

앱 직접 실행 후 브라우저에서 엽니다.

```bash
http://127.0.0.1:8000
```

## 개발

```bash
python3 -m compileall src
```

Linux Mint GNOME 개발 환경 점검:

```bash
./check-system.sh
```
