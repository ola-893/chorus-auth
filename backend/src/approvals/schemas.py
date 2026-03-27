"""
Pydantic schemas for approval workflow APIs.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from ..db.enums import ApprovalStatus, ProviderType


class ApprovalDecisionInput(BaseModel):
    """Body for approval and rejection decisions."""

    reason: str | None = None


class ApprovalQueueItemResponse(BaseModel):
    """Serialized approval queue item."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    action_request_id: str
    agent_id: str
    agent_name: str
    provider: ProviderType
    capability_name: str
    status: ApprovalStatus
    explanation: str | None
    requested_at: datetime
    decided_at: datetime | None
