from __future__ import annotations

from datetime import timedelta

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text

from linux_dashboard.metrics import SystemSnapshot


def render_dashboard(snapshot: SystemSnapshot) -> Group:
    return Group(
        _header(snapshot),
        _resource_grid(snapshot),
        _disk_table(snapshot),
        _process_table(snapshot),
    )


def _header(snapshot: SystemSnapshot) -> Panel:
    uptime = str(timedelta(seconds=int(snapshot.uptime_seconds)))
    body = Text()
    body.append(snapshot.hostname, style="bold cyan")
    body.append(f"  {snapshot.platform}\n", style="white")
    body.append(f"Updated: {snapshot.timestamp:%Y-%m-%d %H:%M:%S}")
    body.append(f"  Uptime: {uptime}")
    return Panel(body, title="Linux Dashboard", border_style="cyan", box=box.ROUNDED)


def _resource_grid(snapshot: SystemSnapshot) -> Table:
    table = Table.grid(expand=True)
    table.add_column(ratio=1)
    table.add_column(ratio=1)
    table.add_column(ratio=1)
    table.add_row(
        _cpu_panel(snapshot),
        _memory_panel(snapshot),
        _network_panel(snapshot),
    )
    return table


def _cpu_panel(snapshot: SystemSnapshot) -> Panel:
    cpu = snapshot.cpu
    load = "n/a" if cpu.load_avg is None else " ".join(f"{value:.2f}" for value in cpu.load_avg)
    freq = "n/a" if cpu.frequency_mhz is None else f"{cpu.frequency_mhz:.0f} MHz"
    lines = [
        _bar("total", cpu.percent),
        f"cores: {cpu.cores_physical or '?'} physical / {cpu.cores_logical} logical",
        f"load: {load}",
        f"freq: {freq}",
    ]
    if cpu.per_core:
        core_text = " ".join(f"{idx}:{value:.0f}%" for idx, value in enumerate(cpu.per_core[:8]))
        lines.append(f"core: {core_text}")
    return Panel(Group(*lines), title="CPU", border_style=_style(cpu.percent), box=box.ROUNDED)


def _memory_panel(snapshot: SystemSnapshot) -> Panel:
    mem = snapshot.memory
    lines = [
        _bar("memory", mem.percent),
        f"used: {_bytes(mem.used)} / {_bytes(mem.total)}",
        f"available: {_bytes(mem.available)}",
        _bar("swap", mem.swap_percent),
        f"swap: {_bytes(mem.swap_used)} / {_bytes(mem.swap_total)}",
    ]
    return Panel(Group(*lines), title="Memory", border_style=_style(mem.percent), box=box.ROUNDED)


def _network_panel(snapshot: SystemSnapshot) -> Panel:
    net = snapshot.network
    lines = [
        f"received: {_bytes(net.bytes_recv)}",
        f"sent:     {_bytes(net.bytes_sent)}",
        f"packets received: {net.packets_recv:,}",
        f"packets sent:     {net.packets_sent:,}",
    ]
    return Panel(Group(*lines), title="Network", border_style="magenta", box=box.ROUNDED)


def _disk_table(snapshot: SystemSnapshot) -> Panel:
    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Mount")
    table.add_column("Type")
    table.add_column("Used", justify="right")
    table.add_column("Free", justify="right")
    table.add_column("Total", justify="right")
    table.add_column("Use", justify="right")

    for disk in snapshot.disks[:8]:
        table.add_row(
            disk.mountpoint,
            disk.fstype,
            _bytes(disk.used),
            _bytes(disk.free),
            _bytes(disk.total),
            f"[{_style(disk.percent)}]{disk.percent:.0f}%[/]",
        )

    return Panel(table, title="Disks", border_style="green", box=box.ROUNDED)


def _process_table(snapshot: SystemSnapshot) -> Panel:
    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("PID", justify="right")
    table.add_column("Name")
    table.add_column("User")
    table.add_column("CPU", justify="right")
    table.add_column("Mem", justify="right")
    table.add_column("Status")

    for process in snapshot.processes:
        table.add_row(
            str(process.pid),
            process.name[:32],
            process.username[:18],
            f"{process.cpu_percent:.1f}%",
            f"{process.memory_percent:.1f}%",
            process.status,
        )

    return Panel(table, title="Top Processes", border_style="yellow", box=box.ROUNDED)


def _bar(label: str, value: float) -> Progress:
    progress = Progress(
        TextColumn(f"{label:<7}"),
        BarColumn(bar_width=None),
        TextColumn(f"{value:>5.1f}%"),
        expand=True,
    )
    progress.add_task(label, total=100, completed=max(0, min(value, 100)))
    return progress


def _style(percent: float) -> str:
    if percent >= 85:
        return "red"
    if percent >= 70:
        return "yellow"
    return "green"


def _bytes(value: int) -> str:
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB", "PiB"):
        if size < 1024 or unit == "PiB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} PiB"

