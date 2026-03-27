"""
FastAPI dependencies for current-user resolution.
"""
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from ..db import get_session
from ..db.models import User
from .adapters import resolve_or_create_user, resolve_user_if_present


def get_current_user(
    request: Request,
    session: Session = Depends(get_session),
) -> User:
    """Resolve and return the current user."""
    return resolve_or_create_user(session, request)


def get_optional_current_user(
    request: Request,
    session: Session = Depends(get_session),
) -> User | None:
    """Resolve the current user when auth material is present."""
    return resolve_user_if_present(session, request)
