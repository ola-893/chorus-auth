"""
Database bootstrap helpers for the auth control plane.
"""
from .base import Base
from .session import engine, prepare_storage_directory
from . import models  # noqa: F401


def create_schema() -> None:
    """Create all tables for local development helpers."""
    prepare_storage_directory()
    Base.metadata.create_all(bind=engine)
