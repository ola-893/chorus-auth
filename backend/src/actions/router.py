"""
Action request API routes.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..auth.adapters import extract_bearer_token
from ..auth.dependencies import get_current_user
from ..db import get_session
from ..db.models import User
from .schemas import ActionDetailResponse, ActionRequestCreate, ActionRequestResponse
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
    request: Request,
    payload: ActionRequestCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ActionRequestResponse:
    """Create and evaluate a new action request."""
    return action_request_service.create_action(
        session,
        current_user,
        payload,
        subject_token=extract_bearer_token(request),
    )


@router.get("/{action_id}", response_model=ActionRequestResponse)
def get_action(
    action_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ActionRequestResponse:
    """Get a single action request."""
    return action_request_service.get_action(session, current_user, action_id)


@router.get("/{action_id}/detail", response_model=ActionDetailResponse)
def get_action_detail(
    action_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ActionDetailResponse:
    """Get a detailed action payload for timeline and drawer views."""
    return action_request_service.get_action_detail(session, current_user, action_id)
