"""
Demo scenario API schemas.
"""
from pydantic import BaseModel


class DemoResetResponse(BaseModel):
    """Response for resetting the seeded demo workspace."""

    user_id: str
    email: str
    connection_count: int
    agent_count: int


class ScenarioRunResult(BaseModel):
    """Response for a seeded demo scenario execution."""

    scenario_id: str
    created_action_ids: list[str]
    final_statuses: list[str]
    highlight_action_id: str | None
