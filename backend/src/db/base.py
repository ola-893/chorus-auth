"""
Shared SQLAlchemy base classes for the auth control plane.
"""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def new_uuid() -> str:
    """Generate a string UUID primary key."""
    return str(uuid4())


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base for all control plane models."""


class PrimaryKeyMixin:
    """Mixin for string UUID primary keys."""

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)


class TimestampMixin:
    """Mixin for created/updated timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
