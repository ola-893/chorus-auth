"""
Database engine and session helpers for the auth control plane.
"""
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ..control_plane_config import settings


def prepare_storage_directory() -> None:
    """Create local SQLite storage directories when needed."""
    if settings.database_url.startswith("sqlite:///"):
        raw_path = settings.database_url.replace("sqlite:///", "", 1)
        database_path = Path(raw_path)
        if not database_path.is_absolute():
            database_path = Path.cwd() / database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)


def create_engine_for_url(url: str) -> Engine:
    """Create an engine for the provided database URL."""
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, future=True, connect_args=connect_args)


prepare_storage_directory()
engine = create_engine_for_url(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session for FastAPI dependencies."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
