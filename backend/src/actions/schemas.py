"""
Pydantic schemas for action request APIs.
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..audit.schemas import AuditEventResponse
from ..db.enums import ActionStatus, ApprovalStatus, EnforcementDecision, ExecutionStatus, ProviderType, RiskLevel


class ActionRequestCreate(BaseModel):
    """Request model for submitting an agent action."""

    agent_id: str
    provider: ProviderType
    capability_name: str
    payload: dict[str, Any] = Field(default_factory=dict)


class ActionRequestResponse(BaseModel):
    """Serialized action request response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    provider: ProviderType
    capability_name: str
    action_type: str
    status: ActionStatus
    enforcement_decision: EnforcementDecision | None
    explanation: str | None
    requested_at: datetime
    resolved_at: datetime | None
    risk_level: RiskLevel | None
    risk_source: str | None
    risk_explanation: str | None
    approval_status: ApprovalStatus | None
    execution_status: ExecutionStatus | None
    execution_mode: str | None
    provider_result_url: str | None
    vault_reference: str | None


class ActionApprovalRecord(BaseModel):
    """Approval detail embedded inside action detail responses."""

    status: ApprovalStatus
    reason: str | None
    decided_at: datetime | None


class ActionExecutionRecord(BaseModel):
    """Execution detail embedded inside action detail responses."""

    status: ExecutionStatus
    summary: str | None
    external_reference_id: str | None
    provider_result_url: str | None
    vault_reference: str | None
    execution_mode: str | None
    executed_at: datetime | None
    result: dict[str, Any]


class ActionConnectionSummary(BaseModel):
    """Connected-account summary embedded inside action detail responses."""

    id: str | None
    provider: ProviderType
    display_label: str | None
    external_account_id: str | None
    vault_reference: str | None
    granted_scopes: list[str]
    mode: str | None


class ActionDetailResponse(BaseModel):
    """Expanded action detail payload for timeline drawers and focused views."""

    action: ActionRequestResponse
    agent_name: str
    approval_record: ActionApprovalRecord | None
    execution_record: ActionExecutionRecord | None
    connection_summary: ActionConnectionSummary | None
    audit_events: list[AuditEventResponse]
