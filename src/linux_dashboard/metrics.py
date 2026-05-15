from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
import platform
import shutil
import socket
import subprocess
import http.client
import json
import urllib.error
import urllib.request
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
class DockerContainerMetrics:
    id: str
    name: str
    image: str
    status: str
    state: str


@dataclass(frozen=True)
class DockerMetrics:
    status: str
    message: str
    version: str | None
    containers: int | None
    containers_running: int | None
    images: int | None
    stopped: list[DockerContainerMetrics]


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
    docker: DockerMetrics
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
        docker=_docker_metrics(),
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


def _docker_metrics() -> DockerMetrics:
    if shutil.which("docker") is None:
        socket_metrics = _docker_socket_metrics()
        if socket_metrics:
            return socket_metrics
        return DockerMetrics(
            status="not_installed",
            message="Docker CLI 또는 Docker 소켓을 찾을 수 없습니다.",
            version=None,
            containers=None,
            containers_running=None,
            images=None,
            stopped=[],
        )

    try:
        result = subprocess.run(
            [
                "docker",
                "info",
                "--format",
                "{{.ServerVersion}}\t{{.Containers}}\t{{.ContainersRunning}}\t{{.Images}}",
            ],
            capture_output=True,
            check=True,
            text=True,
            timeout=2,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        message = str(exc)
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            message = exc.stderr.strip()
        return DockerMetrics(
            status="unavailable",
            message=message or "Docker 상태를 확인할 수 없습니다.",
            version=None,
            containers=None,
            containers_running=None,
            images=None,
            stopped=[],
        )

    fields = result.stdout.strip().split("\t")
    if len(fields) != 4:
        return DockerMetrics(
            status="unavailable",
            message="Docker 응답 형식을 해석할 수 없습니다.",
            version=None,
            containers=None,
            containers_running=None,
            images=None,
            stopped=[],
        )

    version, containers, running, images = fields
    return DockerMetrics(
        status="running",
        message="Docker 데몬이 응답 중입니다.",
        version=version or None,
        containers=_int_or_none(containers),
        containers_running=_int_or_none(running),
        images=_int_or_none(images),
        stopped=_docker_cli_stopped_containers(),
    )


def _docker_socket_metrics() -> DockerMetrics | None:
    socket_path = os.environ.get("DOCKER_HOST_SOCKET", "/var/run/docker.sock")
    if not os.path.exists(socket_path):
        return None

    opener = urllib.request.build_opener(_UnixSocketHandler(socket_path))
    try:
        with opener.open("http://docker/info", timeout=2) as response:
            payload = response.read()
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        return DockerMetrics(
            status="unavailable",
            message=f"Docker 소켓에 연결할 수 없습니다: {exc}",
            version=None,
            containers=None,
            containers_running=None,
            images=None,
            stopped=[],
        )

    try:
        info = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        return DockerMetrics(
            status="unavailable",
            message=f"Docker 응답을 해석할 수 없습니다: {exc}",
            version=None,
            containers=None,
            containers_running=None,
            images=None,
            stopped=[],
        )

    return DockerMetrics(
        status="running",
        message="Docker 소켓이 응답 중입니다.",
        version=info.get("ServerVersion"),
        containers=info.get("Containers"),
        containers_running=info.get("ContainersRunning"),
        images=info.get("Images"),
        stopped=_docker_socket_stopped_containers(socket_path),
    )


def _docker_cli_stopped_containers() -> list[DockerContainerMetrics]:
    try:
        result = subprocess.run(
            [
                "docker",
                "ps",
                "-a",
                "--filter",
                "status=exited",
                "--filter",
                "status=created",
                "--filter",
                "status=dead",
                "--format",
                "{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.State}}",
            ],
            capture_output=True,
            check=True,
            text=True,
            timeout=2,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return []

    containers: list[DockerContainerMetrics] = []
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        if len(fields) != 5:
            continue
        container_id, name, image, status, state = fields
        containers.append(
            DockerContainerMetrics(
                id=container_id,
                name=name,
                image=image,
                status=status,
                state=state,
            )
        )
    return containers


def _docker_socket_stopped_containers(socket_path: str) -> list[DockerContainerMetrics]:
    containers = _docker_socket_json(socket_path, "http://docker/containers/json?all=1")
    if not isinstance(containers, list):
        return []

    stopped: list[DockerContainerMetrics] = []
    for item in containers:
        state = str(item.get("State") or "unknown")
        if state == "running":
            continue
        names = item.get("Names") or []
        name = str(names[0]).lstrip("/") if names else str(item.get("Id") or "unknown")[:12]
        stopped.append(
            DockerContainerMetrics(
                id=str(item.get("Id") or "")[:12],
                name=name,
                image=str(item.get("Image") or "unknown"),
                status=str(item.get("Status") or state),
                state=state,
            )
        )
    return stopped


def _docker_socket_json(socket_path: str, url: str):
    opener = urllib.request.build_opener(_UnixSocketHandler(socket_path))
    try:
        with opener.open(url, timeout=2) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, TimeoutError, UnicodeDecodeError, ValueError):
        return None


class _UnixSocketHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host: str, socket_path: str, timeout=socket._GLOBAL_DEFAULT_TIMEOUT) -> None:
        super().__init__(host, timeout=timeout)
        self.socket_path = socket_path

    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        if self.timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
            self.sock.settimeout(self.timeout)
        self.sock.connect(self.socket_path)


class _UnixSocketHTTPHandler(urllib.request.HTTPHandler):
    def __init__(self, socket_path: str) -> None:
        super().__init__()
        self.socket_path = socket_path

    def http_open(self, req):
        return self.do_open(lambda host, timeout=0: _UnixSocketHTTPConnection(host, self.socket_path, timeout), req)


def _UnixSocketHandler(socket_path: str) -> _UnixSocketHTTPHandler:
    return _UnixSocketHTTPHandler(socket_path)


def _int_or_none(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


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
