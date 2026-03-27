"""
Connected account API routes.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_user
from ..db import get_session
from ..db.models import User
from .schemas import ConnectedAccountCreate, ConnectedAccountResponse
from .service import create_or_update_connection, list_connections

router = APIRouter(prefix="/connections", tags=["connections"])


@router.get("", response_model=list[ConnectedAccountResponse])
def get_connections(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[ConnectedAccountResponse]:
    """List current-user connected accounts."""
    return list_connections(session, current_user)


@router.post("", response_model=ConnectedAccountResponse)
def post_connection(
    payload: ConnectedAccountCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ConnectedAccountResponse:
    """Create or update a connected account."""
    return create_or_update_connection(session, current_user, payload)
