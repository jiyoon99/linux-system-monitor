from __future__ import annotations

import argparse

from rich.console import Console
from rich.live import Live

from linux_dashboard.metrics import collect_snapshot
from linux_dashboard.ui import render_dashboard


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="linux-dashboard",
        description="Terminal UI for Linux system monitoring.",
    )
    parser.add_argument(
        "-i",
        "--interval",
        type=float,
        default=1.0,
        help="Refresh interval in seconds. Default: 1.0",
    )
    parser.add_argument(
        "-t",
        "--top",
        type=int,
        default=8,
        help="Number of top processes to show. Default: 8",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Render one snapshot and exit.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    console = Console()

    if args.once:
        console.print(render_dashboard(collect_snapshot(args.top)))
        return

    with Live(
        render_dashboard(collect_snapshot(args.top)),
        console=console,
        refresh_per_second=max(1, int(1 / max(args.interval, 0.1))),
        screen=True,
    ) as live:
        while True:
            live.update(render_dashboard(collect_snapshot(args.top)))
            live.console.file.flush()
            import time

            time.sleep(max(args.interval, 0.1))


if __name__ == "__main__":
    main()

