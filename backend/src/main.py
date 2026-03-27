"""
CLI entrypoint for the Chorus auth control plane.
"""
from __future__ import annotations

import argparse

import uvicorn

from .control_plane_config import settings


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for the control-plane server."""
    parser = argparse.ArgumentParser(
        description="Run the Chorus auth control plane API.",
    )
    parser.add_argument(
        "--host",
        default=settings.api_host,
        help=f"Host interface to bind. Defaults to {settings.api_host}.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.api_port,
        help=f"Port to bind. Defaults to {settings.api_port}.",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for local development.",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="Uvicorn log level.",
    )
    return parser


def main() -> int:
    """Run the auth control plane API."""
    args = build_parser().parse_args()
    uvicorn.run(
        "src.control_plane_app:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
