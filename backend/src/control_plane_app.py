"""
Lightweight FastAPI entrypoint for the auth control plane runtime.
"""
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy.orm import Session

from .actions.router import router as actions_router
from .agents.router import router as agents_router
from .approvals.router import router as approvals_router
from .audit.router import router as audit_router
from .auth.router import router as auth_router
from .connections.router import router as connections_router
from .control_plane_config import settings
from .db.bootstrap import create_schema, seed_reference_data
from .db.session import SessionLocal, prepare_storage_directory


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
        create_schema()
        session: Session = SessionLocal()
        try:
            seed_reference_data(session)
        finally:
            session.close()

    app.include_router(auth_router, prefix="/api")
    app.include_router(connections_router, prefix="/api")
    app.include_router(agents_router, prefix="/api")
    app.include_router(actions_router, prefix="/api")
    app.include_router(approvals_router, prefix="/api")
    app.include_router(audit_router, prefix="/api")

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
