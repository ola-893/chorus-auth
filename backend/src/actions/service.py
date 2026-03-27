"""
Action request lifecycle service.
"""
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..agents.service import get_agent_for_user
from ..audit.service import append_audit_event
from ..control_plane_config import settings
from ..db.enums import ActionStatus, AgentStatus, ApprovalStatus, EnforcementDecision, ExecutionStatus
from ..db.models import ActionRequest, ApprovalDecision, ExecutionRecord, QuarantineRecord, RiskAssessment, User
from ..enforcement.service import EnforcementEngine
from ..policy.service import PolicyEngine
from ..providers.service import provider_registry
from ..realtime.events import publish_dashboard_event
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
            blocked_count = self._count_previous_blocked_actions(session, agent.id) + 1
            decision = policy.decision
            reason = policy.reason
            threshold = settings.quarantine_after_blocked_requests
            if decision == EnforcementDecision.BLOCK and blocked_count >= threshold:
                decision = EnforcementDecision.QUARANTINE
                reason = "Repeated blocked requests crossed the quarantine threshold."
            self._apply_block_or_quarantine(session, action, agent, user, decision, reason)
            session.commit()
            session.refresh(action)
            response = self.serialize_action(action)
            publish_dashboard_event("action.updated", response.model_dump(mode="json"))
            return response

        action.action_type = policy.capability.action_type
        action.connected_account_id = policy.connected_account.id if policy.connected_account else None
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

        blocked_violation_count = self._count_previous_blocked_actions(session, agent.id) + 1
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
            self._apply_block_or_quarantine(
                session,
                action,
                agent,
                user,
                enforcement.decision,
                enforcement.reason,
            )

        session.commit()
        session.refresh(action)
        response = self.serialize_action(action)
        publish_dashboard_event("action.updated", response.model_dump(mode="json"))
        return response

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

    def execute_after_approval(self, session: Session, user: User, action: ActionRequest) -> None:
        """Resume a pending approval action and execute it."""
        vault = get_vault_adapter()
        access = vault.get_provider_access(user, action.provider, action.connected_account.scopes_json if action.connected_account else [])
        execution = provider_registry.get(action.provider).execute(
            action.capability_name,
            action.payload_json,
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
            agent=action.agent,
            user=user,
            details={"decision": action.enforcement_decision.value if action.enforcement_decision else None},
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

    def _apply_block_or_quarantine(
        self,
        session: Session,
        action: ActionRequest,
        agent,
        user: User,
        decision: EnforcementDecision,
        reason: str,
    ) -> None:
        action.status = ActionStatus.QUARANTINED if decision == EnforcementDecision.QUARANTINE else ActionStatus.POLICY_BLOCKED
        action.enforcement_decision = decision
        action.explanation = reason
        action.resolved_at = datetime.now(timezone.utc)
        self._create_or_update_execution_record(
            session,
            action,
            status=ExecutionStatus.BLOCKED,
            summary=reason,
            external_reference_id=None,
            result={},
        )
        if decision == EnforcementDecision.QUARANTINE:
            agent.status = AgentStatus.QUARANTINED
            agent.quarantined_at = datetime.now(timezone.utc)
            session.add(
                QuarantineRecord(
                    agent_id=agent.id,
                    trigger_action_request_id=action.id,
                    trigger_reason=reason,
                    active=True,
                )
            )
            append_audit_event(
                session,
                "agent.quarantined",
                reason,
                action_request=action,
                agent=agent,
                user=user,
                details={"decision": decision.value},
            )
        append_audit_event(
            session,
            "action.blocked" if decision != EnforcementDecision.QUARANTINE else "action.quarantined",
            reason,
            action_request=action,
            agent=agent,
            user=user,
            details={"decision": decision.value},
        )


action_request_service = ActionRequestService()
