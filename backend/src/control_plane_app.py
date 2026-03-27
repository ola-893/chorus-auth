"""
Lightweight FastAPI entrypoint for the auth control plane runtime.
"""
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .control_plane_config import settings
from .db.session import prepare_storage_directory


def create_app() -> FastAPI:
    """Create the auth control plane API application."""
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Secure authorization, approval, and audit control plane for delegated AI agent actions.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def startup() -> None:
        prepare_storage_directory()

    @app.get("/")
    async def root() -> dict:
        return {
            "name": settings.app_name,
            "pipeline": "auth-control-plane",
            "status": "bootstrapped",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/health")
    async def health() -> dict:
        return {
            "status": "ok",
            "pipeline": "auth-control-plane",
            "environment": settings.environment,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "modes": settings.mode_summary(),
        }

    @app.get("/api/meta")
    async def meta() -> dict:
        return {
            "app_name": settings.app_name,
            "environment": settings.environment,
            "database_url": settings.database_url,
            "redis_url": settings.redis_url,
            "modes": settings.mode_summary(),
        }

    return app
