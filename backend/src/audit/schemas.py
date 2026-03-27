"""
Pydantic schemas for audit events.
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditEventResponse(BaseModel):
    """Serialized audit event response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    action_request_id: str | None
    agent_id: str | None
    user_id: str | None
    event_type: str
    message: str
    details: dict[str, Any]
    occurred_at: datetime
