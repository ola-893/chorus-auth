"""
Dashboard summary schemas.
"""
from pydantic import BaseModel

from ..actions.schemas import ActionRequestResponse


class DashboardSummaryResponse(BaseModel):
    """Top-level dashboard summary payload."""

    auto_approved_count: int
    approval_requested_count: int
    blocked_count: int
    quarantined_count: int
    latest_protected_action: ActionRequestResponse | None
