"""
Approval API routes.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..auth.adapters import extract_bearer_token
from ..auth.dependencies import get_current_user
from ..db import get_session
from ..db.models import User
from .schemas import ApprovalDecisionInput, ApprovalQueueItemResponse
from .service import approval_service

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalQueueItemResponse])
def get_approvals(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[ApprovalQueueItemResponse]:
    """List approval requests for the current user."""
    return approval_service.list_approvals(session, current_user)


@router.post("/{approval_id}/approve", response_model=ApprovalQueueItemResponse)
def approve(
    request: Request,
    approval_id: str,
    payload: ApprovalDecisionInput,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApprovalQueueItemResponse:
    """Approve a pending action."""
    return approval_service.approve(
        session,
        current_user,
        approval_id,
        payload.reason,
        subject_token=extract_bearer_token(request),
    )


@router.post("/{approval_id}/reject", response_model=ApprovalQueueItemResponse)
def reject(
    approval_id: str,
    payload: ApprovalDecisionInput,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApprovalQueueItemResponse:
    """Reject a pending action."""
    return approval_service.reject(session, current_user, approval_id, payload.reason)
