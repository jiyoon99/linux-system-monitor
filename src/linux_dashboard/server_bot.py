from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
import logging
import os
from typing import Any


LOGGER = logging.getLogger("linux_dashboard.server_bot")


@dataclass(frozen=True)
class Thresholds:
    cpu_warn: float
    cpu_fail: float
    memory_warn: float
    memory_fail: float
    disk_warn: float
    disk_fail: float


@dataclass(frozen=True)
class BotAlert:
    level: str
    code: str
    message: str
    value: float | int | str | None
    threshold: float | int | None


def thresholds_from_env() -> Thresholds:
    return Thresholds(
        cpu_warn=_float_env("BOT_CPU_WARN", 85.0),
        cpu_fail=_float_env("BOT_CPU_FAIL", 95.0),
        memory_warn=_float_env("BOT_RAM_WARN", 85.0),
        memory_fail=_float_env("BOT_RAM_FAIL", 95.0),
        disk_warn=_float_env("BOT_DISK_WARN", 90.0),
        disk_fail=_float_env("BOT_DISK_FAIL", 97.0),
    )


def evaluate_alerts(snapshot: dict[str, Any], thresholds: Thresholds | None = None) -> dict[str, Any]:
    limits = thresholds or thresholds_from_env()
    alerts: list[BotAlert] = []

    cpu_percent = _number(snapshot["cpu"]["percent"])
    memory_percent = _number(snapshot["memory"]["percent"])
    disk_percent = _disk_usage_percent(snapshot["disks"])
    docker = snapshot["docker"]
    stopped_containers = list(docker.get("stopped") or [])

    _append_threshold_alert(
        alerts,
        code="cpu_high",
        label="CPU usage",
        value=cpu_percent,
        warn=limits.cpu_warn,
        fail=limits.cpu_fail,
    )
    _append_threshold_alert(
        alerts,
        code="ram_high",
        label="RAM usage",
        value=memory_percent,
        warn=limits.memory_warn,
        fail=limits.memory_fail,
    )
    _append_threshold_alert(
        alerts,
        code="disk_high",
        label="Disk usage",
        value=disk_percent,
        warn=limits.disk_warn,
        fail=limits.disk_fail,
    )

    if docker.get("status") != "running":
        alerts.append(
            BotAlert(
                level="FAIL",
                code="docker_unavailable",
                message=f"Docker is not healthy: {docker.get('message') or 'unknown error'}",
                value=docker.get("status"),
                threshold=None,
            )
        )

    if stopped_containers:
        names = ", ".join(str(item.get("name") or item.get("id") or "unknown") for item in stopped_containers[:5])
        suffix = "" if len(stopped_containers) <= 5 else f" 외 {len(stopped_containers) - 5}개"
        alerts.append(
            BotAlert(
                level="WARN",
                code="docker_stopped_containers",
                message=f"Stopped Docker containers detected: {names}{suffix}",
                value=len(stopped_containers),
                threshold=0,
            )
        )

    status = "FAIL" if any(alert.level == "FAIL" for alert in alerts) else "WARN" if alerts else "OK"
    return {
        "timestamp": datetime.now().isoformat(),
        "status": status,
        "thresholds": asdict(limits),
        "summary": _summary(status, alerts),
        "alerts": [asdict(alert) for alert in alerts],
        "stopped_containers": stopped_containers,
    }


def log_alerts(report: dict[str, Any]) -> None:
    alerts = report.get("alerts") or []
    if not alerts:
        LOGGER.info("OK Server Bot check passed")
        return

    for alert in alerts:
        line = f"{alert['level']} {alert['code']}: {alert['message']}"
        if alert["level"] == "FAIL":
            LOGGER.error(line)
        else:
            LOGGER.warning(line)


def _append_threshold_alert(
    alerts: list[BotAlert],
    *,
    code: str,
    label: str,
    value: float | None,
    warn: float,
    fail: float,
) -> None:
    if value is None:
        return
    if value >= fail:
        alerts.append(
            BotAlert(
                level="FAIL",
                code=code,
                message=f"{label} is critical at {value:.1f}%",
                value=round(value, 1),
                threshold=fail,
            )
        )
    elif value >= warn:
        alerts.append(
            BotAlert(
                level="WARN",
                code=code,
                message=f"{label} is high at {value:.1f}%",
                value=round(value, 1),
                threshold=warn,
            )
        )


def _summary(status: str, alerts: list[BotAlert]) -> str:
    if status == "OK":
        return "Server Bot reports all monitored checks are within thresholds."
    return f"Server Bot found {len(alerts)} issue(s)."


def _disk_usage_percent(disks: list[dict[str, Any]]) -> float | None:
    total = sum(int(disk.get("total") or 0) for disk in disks)
    used = sum(int(disk.get("used") or 0) for disk in disks)
    if total <= 0:
        return None
    return (used / total) * 100


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default
