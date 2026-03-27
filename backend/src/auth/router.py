"""
Auth API routes for resolving the current user.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..control_plane_config import settings
from ..db import get_session
from ..db.models import ConnectedAccount
from .dependencies import get_current_user
from .schemas import CurrentUserResponse

router = APIRouter(tags=["auth"])


@router.get("/me", response_model=CurrentUserResponse)
def get_me(
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CurrentUserResponse:
    """Return the current authenticated user."""
    connection_count = session.scalar(
        select(func.count(ConnectedAccount.id)).where(ConnectedAccount.user_id == current_user.id)
    )

    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        auth_mode=settings.auth_mode,
        connected_account_count=int(connection_count or 0),
    )
