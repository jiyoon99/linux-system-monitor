from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
import shutil
import urllib.error
import urllib.request
from typing import Any


DEFAULT_BASE_URL = "http://host.docker.internal:11434"
DEFAULT_MODEL = "qwen2.5-coder:7b"
DEFAULT_ANALYZE_TIMEOUT = 300
DEFAULT_ANALYZE_NUM_PREDICT = 220


@dataclass(frozen=True)
class OllamaStatus:
    cli_installed: bool
    cli_path: str | None
    server_status: str
    base_url: str
    api_url: str
    version: str | None
    default_model: str
    default_model_available: bool
    models: list[str]
    message: str


def collect_ollama_status() -> dict[str, object]:
    base_url = _base_url()
    api_url = _api_url(base_url)
    default_model = _default_model()
    cli_path = shutil.which("ollama")

    version, version_error = _ollama_version(api_url)
    models, models_error = _ollama_models(api_url)
    server_running = version is not None or models is not None
    model_names = models or []

    if server_running:
        message = "Ollama server is reachable."
        server_status = "running"
    else:
        message = "Ollama server offline"
        if models_error or version_error:
            message = f"{message}: {models_error or version_error}"
        server_status = "offline"

    status = OllamaStatus(
        cli_installed=cli_path is not None,
        cli_path=cli_path,
        server_status=server_status,
        base_url=base_url,
        api_url=api_url,
        version=version,
        default_model=default_model,
        default_model_available=_model_available(model_names, default_model),
        models=model_names,
        message=message,
    )
    return asdict(status)


def collect_ollama_models() -> dict[str, object]:
    status = collect_ollama_status()
    return {
        "server_status": status["server_status"],
        "base_url": status["base_url"],
        "models": status["models"],
        "default_model": status["default_model"],
        "default_model_available": status["default_model_available"],
        "message": status["message"],
    }


def analyze_system(snapshot: dict[str, Any], model: str | None = None) -> dict[str, object]:
    status = collect_ollama_status()
    selected_model = model or _default_model()
    if status["server_status"] != "running":
        return {
            "ok": False,
            "error": "Ollama server offline",
            "status": status,
            "analysis": None,
        }

    if not _model_available(list(status["models"]), selected_model):
        return {
            "ok": False,
            "error": f"Model not found: {selected_model}",
            "hint": f"Run: ollama run {selected_model}",
            "status": status,
            "analysis": None,
        }

    prompt = _analysis_prompt(snapshot)
    payload = {
        "model": selected_model,
        "stream": False,
        "options": {
            "num_predict": _analyze_num_predict(),
            "temperature": 0.2,
        },
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a cautious Linux server operations assistant. Reply in Korean. "
                    "Keep the answer concise. Do not suggest destructive commands."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    }
    response, error = _post_json(f"{status['api_url']}/chat", payload, timeout=_analyze_timeout())
    if error:
        return {
            "ok": False,
            "error": error,
            "status": status,
            "analysis": None,
        }

    analysis = ""
    if isinstance(response, dict):
        message = response.get("message")
        if isinstance(message, dict):
            analysis = str(message.get("content") or "").strip()

    return {
        "ok": True,
        "model": selected_model,
        "status": status,
        "analysis": analysis or "Ollama returned an empty analysis.",
    }


def _analysis_prompt(snapshot: dict[str, Any]) -> str:
    docker = snapshot["docker"]
    stopped = docker.get("stopped") or []
    stopped_names = [str(item.get("name")) for item in stopped if isinstance(item, dict) and item.get("name")]
    disk_total = sum(int(item.get("total") or 0) for item in snapshot["disks"])
    disk_used = sum(int(item.get("used") or 0) for item in snapshot["disks"])
    disk_percent = (disk_used / disk_total) * 100 if disk_total else 0.0

    summary = {
        "timestamp": snapshot["timestamp"],
        "hostname": snapshot["hostname"],
        "platform": snapshot["platform"],
        "uptime_seconds": snapshot["uptime_seconds"],
        "cpu": {
            "percent": snapshot["cpu"]["percent"],
            "load_avg": snapshot["cpu"]["load_avg"],
            "cores_logical": snapshot["cpu"]["cores_logical"],
        },
        "ram": {
            "percent": snapshot["memory"]["percent"],
            "used": snapshot["memory"]["used"],
            "total": snapshot["memory"]["total"],
        },
        "disk": {
            "percent": round(disk_percent, 1),
            "used": disk_used,
            "total": disk_total,
            "mounts": len(snapshot["disks"]),
        },
        "docker": {
            "status": docker.get("status"),
            "containers": docker.get("containers"),
            "containers_running": docker.get("containers_running"),
            "stopped_containers": stopped_names[:8],
        },
    }
    return (
        "아래 서버 메트릭을 6줄 이내로 분석해줘. "
        "형식: 상태요약 2줄, 위험신호 2줄, 안전한 다음조치 2줄. "
        "불필요한 설명은 생략해줘.\n\n"
        f"{json.dumps(summary, ensure_ascii=False, separators=(',', ':'))}"
    )


def _ollama_version(api_url: str) -> tuple[str | None, str | None]:
    payload, error = _get_json(f"{api_url}/version")
    if error:
        return None, error
    if isinstance(payload, dict):
        version = payload.get("version")
        return str(version) if version else None, None
    return None, "Ollama version response was not an object."


def _ollama_models(api_url: str) -> tuple[list[str] | None, str | None]:
    payload, error = _get_json(f"{api_url}/tags")
    if error:
        return None, error
    if not isinstance(payload, dict):
        return None, "Ollama tags response was not an object."

    models = payload.get("models")
    if not isinstance(models, list):
        return [], None

    names = [str(item.get("name")) for item in models if isinstance(item, dict) and item.get("name")]
    return sorted(names), None


def _get_json(url: str, timeout: float = 2) -> tuple[object | None, str | None]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8")), None
    except (OSError, urllib.error.URLError, TimeoutError, UnicodeDecodeError, ValueError) as exc:
        return None, str(exc)


def _post_json(url: str, payload: dict[str, object], timeout: float = 60) -> tuple[object | None, str | None]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8")), None
    except (OSError, urllib.error.URLError, TimeoutError, UnicodeDecodeError, ValueError) as exc:
        return None, str(exc)


def _model_available(models: list[str], required_model: str) -> bool:
    if ":" in required_model:
        return required_model in models
    return any(model == required_model or model.startswith(f"{required_model}:") for model in models)


def _base_url() -> str:
    value = os.environ.get("OLLAMA_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/")
    if value.endswith("/api"):
        value = value[:-4]
    return value or DEFAULT_BASE_URL


def _api_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/api"


def _default_model() -> str:
    return os.environ.get("OLLAMA_MODEL", os.environ.get("OLLAMA_REQUIRED_MODEL", DEFAULT_MODEL)).strip() or DEFAULT_MODEL


def _analyze_timeout() -> float:
    value = os.environ.get("OLLAMA_ANALYZE_TIMEOUT", "").strip()
    if not value:
        return DEFAULT_ANALYZE_TIMEOUT
    try:
        return max(5.0, float(value))
    except ValueError:
        return DEFAULT_ANALYZE_TIMEOUT


def _analyze_num_predict() -> int:
    value = os.environ.get("OLLAMA_ANALYZE_NUM_PREDICT", "").strip()
    if not value:
        return DEFAULT_ANALYZE_NUM_PREDICT
    try:
        return max(64, int(value))
    except ValueError:
        return DEFAULT_ANALYZE_NUM_PREDICT
