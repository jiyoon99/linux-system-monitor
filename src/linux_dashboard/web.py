from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict
from collections import deque
from importlib.resources import files
import logging
from threading import Lock
from typing import Any

from fastapi import FastAPI, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

from linux_dashboard.metrics import collect_snapshot
from linux_dashboard.ollama_monitor import analyze_system, collect_ollama_models, collect_ollama_status
from linux_dashboard.server_bot import evaluate_alerts, log_alerts


STATIC_DIR = files("linux_dashboard").joinpath("static")
TEMPLATE_DIR = files("linux_dashboard").joinpath("templates")

app = FastAPI(title="Linux Dashboard", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
METRICS_HISTORY_LIMIT = 60
BOT_CHECK_INTERVAL_SECONDS = 30
_history_lock = Lock()
_metrics_history: deque[dict[str, Any]] = deque(maxlen=METRICS_HISTORY_LIMIT)
_alerts_lock = Lock()
_latest_alerts: dict[str, Any] | None = None


class OllamaAnalyzeRequest(BaseModel):
    model: str | None = None


@app.on_event("startup")
async def startup() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    asyncio.create_task(_bot_monitor_loop())


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "title": "Linux System Dashboard",
            "refresh_interval_ms": 2000,
            "top_processes": 8,
        },
    )


@app.get("/api/snapshot")
def snapshot(top: int = Query(default=8, ge=1, le=50)) -> dict[str, Any]:
    return _snapshot_dict(top)


@app.get("/api/metrics")
def metrics(top: int = Query(default=8, ge=1, le=50)) -> dict[str, Any]:
    current = _snapshot_dict(top)
    bot_report = _evaluate_and_store_alerts(current)
    ollama_report = collect_ollama_status()

    with _history_lock:
        sample = _history_sample(current, _metrics_history[-1] if _metrics_history else None)
        _metrics_history.append(sample)
        history = list(_metrics_history)

    return {
        "current": current,
        "history": history,
        "alerts": bot_report,
        "ollama": ollama_report,
        "interval_seconds": 2,
        "max_points": METRICS_HISTORY_LIMIT,
    }


@app.get("/api/alerts")
def alerts() -> dict[str, Any]:
    report = _latest_alert_report()
    if report:
        return report
    return _evaluate_and_store_alerts(_snapshot_dict(top=8))


@app.get("/api/ollama")
def ollama() -> dict[str, object]:
    return collect_ollama_status()


@app.get("/api/ollama/status")
def ollama_status() -> dict[str, object]:
    return collect_ollama_status()


@app.get("/api/ollama/models")
def ollama_models() -> dict[str, object]:
    return collect_ollama_models()


@app.post("/api/ollama/analyze")
def ollama_analyze(request: OllamaAnalyzeRequest | None = None) -> dict[str, object]:
    model = request.model if request else None
    return analyze_system(_snapshot_dict(top=8), model=model)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


def _snapshot_dict(top: int) -> dict[str, Any]:
    data = asdict(collect_snapshot(top))
    data["timestamp"] = data["timestamp"].isoformat()
    return data


def _evaluate_and_store_alerts(snapshot_data: dict[str, Any]) -> dict[str, Any]:
    report = evaluate_alerts(snapshot_data)
    with _alerts_lock:
        global _latest_alerts
        _latest_alerts = report
    return report


def _latest_alert_report() -> dict[str, Any] | None:
    with _alerts_lock:
        return _latest_alerts


async def _bot_monitor_loop() -> None:
    logger = logging.getLogger("linux_dashboard.server_bot")
    while True:
        try:
            report = _evaluate_and_store_alerts(_snapshot_dict(top=8))
            log_alerts(report)
        except Exception:
            logger.exception("FAIL server_bot_check_error")
        await asyncio.sleep(BOT_CHECK_INTERVAL_SECONDS)


def _history_sample(data: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
    network = data["network"]
    disk_usage = _disk_usage_percent(data["disks"])
    sample = {
        "timestamp": data["timestamp"],
        "cpu_percent": data["cpu"]["percent"],
        "memory_percent": data["memory"]["percent"],
        "disk_percent": disk_usage,
        "bytes_recv": network["bytes_recv"],
        "bytes_sent": network["bytes_sent"],
        "recv_rate": 0.0,
        "sent_rate": 0.0,
    }

    if previous:
        elapsed = max(
            _timestamp_seconds(sample["timestamp"]) - _timestamp_seconds(previous["timestamp"]),
            0.001,
        )
        sample["recv_rate"] = max((sample["bytes_recv"] - previous["bytes_recv"]) / elapsed, 0.0)
        sample["sent_rate"] = max((sample["bytes_sent"] - previous["bytes_sent"]) / elapsed, 0.0)

    return sample


def _disk_usage_percent(disks: list[dict[str, Any]]) -> float | None:
    total = sum(int(disk.get("total") or 0) for disk in disks)
    used = sum(int(disk.get("used") or 0) for disk in disks)
    if total <= 0:
        return None
    return (used / total) * 100


def _timestamp_seconds(value: str) -> float:
    from datetime import datetime

    return datetime.fromisoformat(value).timestamp()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="linux-dashboard-web",
        description="Web dashboard for Linux system monitoring.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host. Default: 127.0.0.1")
    parser.add_argument("--port", type=int, default=8000, help="Bind port. Default: 8000")
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn reload.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    uvicorn.run(
        "linux_dashboard.web:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
