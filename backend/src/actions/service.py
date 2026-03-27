"""
Action request lifecycle service.
"""
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..agents.service import get_agent_for_user
from ..audit.service import append_audit_event
from ..db.enums import ActionStatus, ApprovalStatus, EnforcementDecision, ExecutionStatus
from ..db.models import ActionRequest, ApprovalDecision, ExecutionRecord, RiskAssessment, User
from ..enforcement.service import EnforcementEngine
from ..policy.service import PolicyEngine
from ..providers.service import provider_registry
from ..risk.service import RiskEngine
from ..vault.adapters import get_vault_adapter
from .schemas import ActionRequestCreate, ActionRequestResponse


class ActionRequestService:
    """End-to-end lifecycle for control-plane action requests."""

    def __init__(self) -> None:
        self.policy_engine = PolicyEngine()
        self.risk_engine = RiskEngine()
        self.enforcement_engine = EnforcementEngine()

    def create_action(self, session: Session, user: User, payload: ActionRequestCreate) -> ActionRequestResponse:
        agent = get_agent_for_user(session, user, payload.agent_id)
        action = ActionRequest(
            owner_user_id=user.id,
            agent_id=agent.id,
            provider=payload.provider,
            capability_name=payload.capability_name,
            action_type=payload.capability_name,
            payload_json=payload.payload,
            status=ActionStatus.RECEIVED,
        )
        session.add(action)
        session.flush()

        append_audit_event(
            session,
            "action.created",
            "Action request received.",
            action_request=action,
            agent=agent,
            user=user,
            details={"provider": payload.provider.value, "capability_name": payload.capability_name},
        )

        policy = self.policy_engine.evaluate(
            session,
            user,
            agent,
            payload.provider,
            payload.capability_name,
            payload.payload,
        )

        if not policy.allowed:
            action.status = ActionStatus.QUARANTINED if policy.decision == EnforcementDecision.QUARANTINE else ActionStatus.POLICY_BLOCKED
            action.enforcement_decision = policy.decision
            action.explanation = policy.reason
            action.resolved_at = datetime.now(timezone.utc)
            self._create_or_update_execution_record(
                session,
                action,
                status=ExecutionStatus.BLOCKED,
                summary=policy.reason,
                external_reference_id=None,
                result={},
            )
            append_audit_event(
                session,
                "action.blocked",
                policy.reason,
                action_request=action,
                agent=agent,
                user=user,
                details={"decision": policy.decision.value},
            )
            session.commit()
            session.refresh(action)
            return self.serialize_action(action)

        action.action_type = policy.capability.action_type
        risk = self.risk_engine.assess(agent, policy.capability, payload.payload, policy.reason)
        session.add(
            RiskAssessment(
                action_request_id=action.id,
                score=risk.score,
                level=risk.level,
                source=risk.source,
                explanation=risk.explanation,
                recommendation=risk.recommendation,
                confidence=risk.confidence,
                assessment_metadata_json={"provider": payload.provider.value},
            )
        )

        blocked_violation_count = self._count_previous_blocked_actions(session, agent.id)
        enforcement = self.enforcement_engine.decide(
            policy,
            risk,
            blocked_violation_count=blocked_violation_count,
        )
        action.enforcement_decision = enforcement.decision
        action.explanation = enforcement.reason

        if enforcement.decision in {EnforcementDecision.ALLOW, EnforcementDecision.ALLOW_WITH_AUDIT}:
            vault = get_vault_adapter()
            access = vault.get_provider_access(user, payload.provider, policy.connected_account.scopes_json)
            execution = provider_registry.get(payload.provider).execute(
                payload.capability_name,
                payload.payload,
                access,
            )
            action.status = ActionStatus.COMPLETED if execution.success else ActionStatus.FAILED
            action.resolved_at = datetime.now(timezone.utc)
            self._create_or_update_execution_record(
                session,
                action,
                status=ExecutionStatus.SUCCEEDED if execution.success else ExecutionStatus.FAILED,
                summary=execution.summary,
                external_reference_id=execution.external_reference_id,
                result=execution.payload,
            )
            append_audit_event(
                session,
                "action.executed",
                execution.summary,
                action_request=action,
                agent=agent,
                user=user,
                details={"decision": enforcement.decision.value},
            )
        elif enforcement.decision == EnforcementDecision.REQUIRE_APPROVAL:
            action.status = ActionStatus.PENDING_APPROVAL
            session.add(
                ApprovalDecision(
                    action_request_id=action.id,
                    status=ApprovalStatus.PENDING,
                )
            )
            append_audit_event(
                session,
                "action.pending_approval",
                enforcement.reason,
                action_request=action,
                agent=agent,
                user=user,
                details={"decision": enforcement.decision.value},
            )
        else:
            action.status = ActionStatus.POLICY_BLOCKED
            action.resolved_at = datetime.now(timezone.utc)
            self._create_or_update_execution_record(
                session,
                action,
                status=ExecutionStatus.BLOCKED,
                summary=enforcement.reason,
                external_reference_id=None,
                result={},
            )
            append_audit_event(
                session,
                "action.blocked",
                enforcement.reason,
                action_request=action,
                agent=agent,
                user=user,
                details={"decision": enforcement.decision.value},
            )

        session.commit()
        session.refresh(action)
        return self.serialize_action(action)

    def list_actions(self, session: Session, user: User) -> list[ActionRequestResponse]:
        actions = session.scalars(
            select(ActionRequest)
            .where(ActionRequest.owner_user_id == user.id)
            .order_by(ActionRequest.requested_at.desc())
        ).all()
        return [self.serialize_action(action) for action in actions]

    def get_action(self, session: Session, user: User, action_id: str) -> ActionRequestResponse:
        action = session.scalar(
            select(ActionRequest).where(
                ActionRequest.id == action_id,
                ActionRequest.owner_user_id == user.id,
            )
        )
        if action is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Action request not found",
            )
        return self.serialize_action(action)

    def serialize_action(self, action: ActionRequest) -> ActionRequestResponse:
        risk_level = None
        approval_status = None
        execution_status = None
        if action.risk_assessment is not None:
            risk_level = action.risk_assessment.level
        if action.approval_decision is not None:
            approval_status = action.approval_decision.status
        if action.execution_record is not None:
            execution_status = action.execution_record.status

        return ActionRequestResponse(
            id=action.id,
            agent_id=action.agent_id,
            provider=action.provider,
            capability_name=action.capability_name,
            action_type=action.action_type,
            status=action.status,
            enforcement_decision=action.enforcement_decision,
            explanation=action.explanation,
            requested_at=action.requested_at,
            resolved_at=action.resolved_at,
            risk_level=risk_level,
            approval_status=approval_status,
            execution_status=execution_status,
        )

    def _create_or_update_execution_record(
        self,
        session: Session,
        action: ActionRequest,
        *,
        status: ExecutionStatus,
        summary: str,
        external_reference_id: str | None,
        result: dict,
    ) -> None:
        execution = action.execution_record
        if execution is None:
            execution = ExecutionRecord(action_request_id=action.id)
            session.add(execution)
        execution.status = status
        execution.provider_response_summary = summary
        execution.external_reference_id = external_reference_id
        execution.executed_at = datetime.now(timezone.utc)
        execution.result_json = result

    def _count_previous_blocked_actions(self, session: Session, agent_id: str) -> int:
        return int(
            session.scalar(
                select(func.count(ActionRequest.id)).where(
                    ActionRequest.agent_id == agent_id,
                    ActionRequest.status.in_([ActionStatus.POLICY_BLOCKED, ActionStatus.QUARANTINED]),
                )
            )
            or 0
        )


action_request_service = ActionRequestService()
