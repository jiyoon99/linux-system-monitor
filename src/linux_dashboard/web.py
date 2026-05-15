from __future__ import annotations

import argparse
from dataclasses import asdict
from importlib.resources import files
from typing import Any

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from linux_dashboard.metrics import collect_snapshot


STATIC_DIR = files("linux_dashboard").joinpath("static")

app = FastAPI(title="Linux Dashboard", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(STATIC_DIR.joinpath("index.html")))


@app.get("/api/snapshot")
def snapshot(top: int = Query(default=8, ge=1, le=50)) -> dict[str, Any]:
    data = asdict(collect_snapshot(top))
    data["timestamp"] = data["timestamp"].isoformat()
    return data


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
