from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
import platform
from typing import Iterable

import psutil

if host_proc := os.environ.get("HOST_PROC"):
    psutil.PROCFS_PATH = host_proc


@dataclass(frozen=True)
class CpuMetrics:
    percent: float
    per_core: list[float]
    load_avg: tuple[float, float, float] | None
    frequency_mhz: float | None
    cores_logical: int
    cores_physical: int | None


@dataclass(frozen=True)
class MemoryMetrics:
    total: int
    used: int
    available: int
    percent: float
    swap_total: int
    swap_used: int
    swap_percent: float


@dataclass(frozen=True)
class DiskMetrics:
    mountpoint: str
    fstype: str
    total: int
    used: int
    free: int
    percent: float


@dataclass(frozen=True)
class NetworkMetrics:
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int


@dataclass(frozen=True)
class ProcessMetrics:
    pid: int
    name: str
    username: str
    cpu_percent: float
    memory_percent: float
    status: str


@dataclass(frozen=True)
class SystemSnapshot:
    timestamp: datetime
    hostname: str
    platform: str
    uptime_seconds: float
    cpu: CpuMetrics
    memory: MemoryMetrics
    disks: list[DiskMetrics]
    network: NetworkMetrics
    processes: list[ProcessMetrics]


def collect_snapshot(top_processes: int = 8) -> SystemSnapshot:
    return SystemSnapshot(
        timestamp=datetime.now(),
        hostname=platform.node() or "unknown",
        platform=_platform_label(),
        uptime_seconds=datetime.now().timestamp() - psutil.boot_time(),
        cpu=_cpu_metrics(),
        memory=_memory_metrics(),
        disks=list(_disk_metrics()),
        network=_network_metrics(),
        processes=_process_metrics(top_processes),
    )


def _platform_label() -> str:
    parts = [platform.system(), platform.release(), platform.machine()]
    return " ".join(part for part in parts if part)


def _cpu_metrics() -> CpuMetrics:
    freq = psutil.cpu_freq()
    try:
        load_avg = os.getloadavg()
    except OSError:
        load_avg = None

    return CpuMetrics(
        percent=psutil.cpu_percent(interval=None),
        per_core=psutil.cpu_percent(interval=None, percpu=True),
        load_avg=load_avg,
        frequency_mhz=freq.current if freq else None,
        cores_logical=psutil.cpu_count(logical=True) or 0,
        cores_physical=psutil.cpu_count(logical=False),
    )


def _memory_metrics() -> MemoryMetrics:
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return MemoryMetrics(
        total=mem.total,
        used=mem.used,
        available=mem.available,
        percent=mem.percent,
        swap_total=swap.total,
        swap_used=swap.used,
        swap_percent=swap.percent,
    )


def _disk_metrics() -> Iterable[DiskMetrics]:
    seen: set[str] = set()
    for partition in psutil.disk_partitions(all=False):
        if partition.mountpoint in seen:
            continue
        seen.add(partition.mountpoint)
        usage_path = _host_path(partition.mountpoint)
        try:
            usage = psutil.disk_usage(usage_path)
        except (PermissionError, OSError):
            continue
        yield DiskMetrics(
            mountpoint=partition.mountpoint,
            fstype=partition.fstype or "unknown",
            total=usage.total,
            used=usage.used,
            free=usage.free,
            percent=usage.percent,
        )


def _host_path(path: str) -> str:
    host_root = os.environ.get("HOST_ROOT")
    if not host_root or path == "/":
        return host_root or path
    return os.path.join(host_root, path.lstrip("/"))


def _network_metrics() -> NetworkMetrics:
    counters = psutil.net_io_counters()
    return NetworkMetrics(
        bytes_sent=counters.bytes_sent,
        bytes_recv=counters.bytes_recv,
        packets_sent=counters.packets_sent,
        packets_recv=counters.packets_recv,
    )


def _process_metrics(limit: int) -> list[ProcessMetrics]:
    processes: list[ProcessMetrics] = []
    attrs = ["pid", "name", "username", "cpu_percent", "memory_percent", "status"]
    for process in psutil.process_iter(attrs=attrs):
        try:
            info = process.info
            processes.append(
                ProcessMetrics(
                    pid=int(info.get("pid") or 0),
                    name=str(info.get("name") or "unknown"),
                    username=str(info.get("username") or "unknown"),
                    cpu_percent=float(info.get("cpu_percent") or 0.0),
                    memory_percent=float(info.get("memory_percent") or 0.0),
                    status=str(info.get("status") or "unknown"),
                )
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return sorted(
        processes,
        key=lambda item: (item.cpu_percent, item.memory_percent),
        reverse=True,
    )[: max(limit, 1)]
