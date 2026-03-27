"""
Action request API routes.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_user
from ..db import get_session
from ..db.models import User
from .schemas import ActionRequestCreate, ActionRequestResponse
from .service import action_request_service

router = APIRouter(prefix="/actions", tags=["actions"])


@router.get("", response_model=list[ActionRequestResponse])
def get_actions(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[ActionRequestResponse]:
    """List current-user action requests."""
    return action_request_service.list_actions(session, current_user)


@router.post("", response_model=ActionRequestResponse)
def post_action(
    payload: ActionRequestCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ActionRequestResponse:
    """Create and evaluate a new action request."""
    return action_request_service.create_action(session, current_user, payload)


@router.get("/{action_id}", response_model=ActionRequestResponse)
def get_action(
    action_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ActionRequestResponse:
    """Get a single action request."""
    return action_request_service.get_action(session, current_user, action_id)
