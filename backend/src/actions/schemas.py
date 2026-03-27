"""
Pydantic schemas for action request APIs.
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

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
    approval_status: ApprovalStatus | None
    execution_status: ExecutionStatus | None
