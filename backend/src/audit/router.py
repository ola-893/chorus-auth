"""
Audit API routes.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_user
from ..db import get_session
from ..db.models import User
from .schemas import AuditEventResponse
from .service import list_audit_events, list_audit_events_for_action

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditEventResponse])
def get_audit(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[AuditEventResponse]:
    """Return the current user's audit timeline."""
    return list_audit_events(session, current_user)


@router.get("/{action_id}", response_model=list[AuditEventResponse])
def get_action_audit(
    action_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[AuditEventResponse]:
    """Return audit events for a specific action."""
    return list_audit_events_for_action(session, current_user, action_id)
