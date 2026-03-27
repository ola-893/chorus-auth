"""
Approval workflow service.
"""
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..actions.service import action_request_service
from ..audit.service import append_audit_event
from ..db.enums import ActionStatus, ApprovalStatus
from ..db.models import ActionRequest, ApprovalDecision, User
from .schemas import ApprovalQueueItemResponse


class ApprovalService:
    """List and resolve approval requests."""

    def list_approvals(self, session: Session, user: User) -> list[ApprovalQueueItemResponse]:
        approvals = session.scalars(
            select(ApprovalDecision)
            .join(ActionRequest, ApprovalDecision.action_request_id == ActionRequest.id)
            .where(ActionRequest.owner_user_id == user.id)
            .options(joinedload(ApprovalDecision.action_request).joinedload(ActionRequest.agent))
            .order_by(ApprovalDecision.created_at.desc())
        ).all()
        return [self.serialize_approval(approval) for approval in approvals]

    def approve(
        self,
        session: Session,
        user: User,
        approval_id: str,
        reason: str | None,
    ) -> ApprovalQueueItemResponse:
        approval = self._get_approval(session, user, approval_id)
        if approval.status != ApprovalStatus.PENDING:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Approval is already resolved")

        approval.status = ApprovalStatus.APPROVED
        approval.approver_user_id = user.id
        approval.reason = reason
        approval.decided_at = datetime.now(timezone.utc)
        append_audit_event(
            session,
            "approval.approved",
            reason or "Approval granted.",
            action_request=approval.action_request,
            agent=approval.action_request.agent,
            user=user,
            details={"approval_id": approval.id},
        )
        action_request_service.execute_after_approval(session, user, approval.action_request)
        session.commit()
        session.refresh(approval)
        return self.serialize_approval(approval)

    def reject(
        self,
        session: Session,
        user: User,
        approval_id: str,
        reason: str | None,
    ) -> ApprovalQueueItemResponse:
        approval = self._get_approval(session, user, approval_id)
        if approval.status != ApprovalStatus.PENDING:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Approval is already resolved")

        approval.status = ApprovalStatus.REJECTED
        approval.approver_user_id = user.id
        approval.reason = reason
        approval.decided_at = datetime.now(timezone.utc)
        approval.action_request.status = ActionStatus.REJECTED
        approval.action_request.resolved_at = datetime.now(timezone.utc)
        append_audit_event(
            session,
            "approval.rejected",
            reason or "Approval rejected.",
            action_request=approval.action_request,
            agent=approval.action_request.agent,
            user=user,
            details={"approval_id": approval.id},
        )
        session.commit()
        session.refresh(approval)
        return self.serialize_approval(approval)

    def serialize_approval(self, approval: ApprovalDecision) -> ApprovalQueueItemResponse:
        action = approval.action_request
        return ApprovalQueueItemResponse(
            id=approval.id,
            action_request_id=action.id,
            agent_id=action.agent.id,
            agent_name=action.agent.name,
            provider=action.provider,
            capability_name=action.capability_name,
            status=approval.status,
            explanation=action.explanation,
            requested_at=action.requested_at,
            decided_at=approval.decided_at,
        )

    def _get_approval(self, session: Session, user: User, approval_id: str) -> ApprovalDecision:
        approval = session.scalar(
            select(ApprovalDecision)
            .join(ActionRequest, ApprovalDecision.action_request_id == ActionRequest.id)
            .where(
                ApprovalDecision.id == approval_id,
                ActionRequest.owner_user_id == user.id,
            )
            .options(joinedload(ApprovalDecision.action_request).joinedload(ActionRequest.agent))
        )
        if approval is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found")
        return approval


approval_service = ApprovalService()
