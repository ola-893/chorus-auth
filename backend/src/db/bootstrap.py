"""
Database bootstrap helpers for the auth control plane.
"""
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from ..agents.service import ensure_capability_catalog
from .base import Base
from .session import engine, prepare_storage_directory
from . import models  # noqa: F401


def create_schema() -> None:
    """Create all tables for local development helpers."""
    prepare_storage_directory()
    _reset_sqlite_schema_when_outdated()
    Base.metadata.create_all(bind=engine)


def seed_reference_data(session: Session) -> None:
    """Seed static reference data required by the control plane."""
    ensure_capability_catalog(session)


def _reset_sqlite_schema_when_outdated() -> None:
    """Recreate local SQLite demo schemas when tracked columns drift."""
    if engine.url.get_backend_name() != "sqlite":
        return

    inspector = inspect(engine)
    if not inspector.has_table("connected_accounts"):
        return

    expected_columns = {
        "connected_accounts": {
            "display_label",
            "connection_health",
            "vault_reference",
            "last_synced_at",
        },
        "execution_records": {
            "provider_result_url",
            "vault_reference",
            "execution_mode",
        },
    }

    for table_name, required_columns in expected_columns.items():
        actual_columns = {column["name"] for column in inspector.get_columns(table_name)}
        if not required_columns.issubset(actual_columns):
            Base.metadata.drop_all(bind=engine)
            return
