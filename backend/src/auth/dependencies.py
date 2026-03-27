"""
FastAPI dependencies for current-user resolution.
"""
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from ..db import get_session
from ..db.models import User
from .adapters import resolve_or_create_user


def get_current_user(
    request: Request,
    session: Session = Depends(get_session),
) -> User:
    """Resolve and return the current user."""
    return resolve_or_create_user(session, request)
