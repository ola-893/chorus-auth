"""
Database bootstrap helpers for the auth control plane.
"""
from sqlalchemy.orm import Session

from ..agents.service import ensure_capability_catalog
from .base import Base
from .session import engine, prepare_storage_directory
from . import models  # noqa: F401


def create_schema() -> None:
    """Create all tables for local development helpers."""
    prepare_storage_directory()
    Base.metadata.create_all(bind=engine)


def seed_reference_data(session: Session) -> None:
    """Seed static reference data required by the control plane."""
    ensure_capability_catalog(session)
