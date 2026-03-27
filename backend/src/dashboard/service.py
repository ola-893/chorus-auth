"""
Dashboard summary service.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..actions.service import action_request_service
from ..db.enums import ActionStatus, AgentStatus, EnforcementDecision
from ..db.models import ActionRequest, Agent, User
from .schemas import DashboardSummaryResponse


def build_dashboard_summary(session: Session, user: User) -> DashboardSummaryResponse:
    """Aggregate top-level dashboard counts and the latest protected action."""
    auto_approved_count = int(
        session.scalar(
            select(func.count(ActionRequest.id)).where(
                ActionRequest.owner_user_id == user.id,
                ActionRequest.enforcement_decision.in_(
                    [EnforcementDecision.ALLOW, EnforcementDecision.ALLOW_WITH_AUDIT]
                ),
                ActionRequest.status == ActionStatus.COMPLETED,
            )
        )
        or 0
    )
    approval_requested_count = int(
        session.scalar(
            select(func.count(ActionRequest.id)).where(
                ActionRequest.owner_user_id == user.id,
                ActionRequest.enforcement_decision == EnforcementDecision.REQUIRE_APPROVAL,
            )
        )
        or 0
    )
    blocked_count = int(
        session.scalar(
            select(func.count(ActionRequest.id)).where(
                ActionRequest.owner_user_id == user.id,
                ActionRequest.enforcement_decision == EnforcementDecision.BLOCK,
            )
        )
        or 0
    )
    quarantined_count = int(
        session.scalar(
            select(func.count(Agent.id)).where(
                Agent.owner_user_id == user.id,
                Agent.status == AgentStatus.QUARANTINED,
            )
        )
        or 0
    )

    latest_protected_action_model = session.scalar(
        select(ActionRequest)
        .where(
            ActionRequest.owner_user_id == user.id,
            ActionRequest.enforcement_decision.in_(
                [
                    EnforcementDecision.REQUIRE_APPROVAL,
                    EnforcementDecision.BLOCK,
                    EnforcementDecision.QUARANTINE,
                ]
            ),
        )
        .options(*action_request_service._action_load_options())
        .order_by(ActionRequest.requested_at.desc())
        .limit(1)
    )
    latest_protected_action = (
        action_request_service.serialize_action(latest_protected_action_model)
        if latest_protected_action_model is not None
        else None
    )

    return DashboardSummaryResponse(
        auto_approved_count=auto_approved_count,
        approval_requested_count=approval_requested_count,
        blocked_count=blocked_count,
        quarantined_count=quarantined_count,
        latest_protected_action=latest_protected_action,
    )
