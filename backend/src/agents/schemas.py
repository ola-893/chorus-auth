"""
Pydantic schemas for agent registry and capability grants.
"""
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..db.enums import AgentStatus, ProviderType, RiskLevel


class AgentCreate(BaseModel):
    """Request model for creating an agent."""

    name: str
    agent_type: str
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityGrantCreate(BaseModel):
    """Request model for granting a capability to an agent."""

    capability_name: str
    constraints: dict[str, Any] = Field(default_factory=dict)


class CapabilityGrantResponse(BaseModel):
    """Capability grant response model."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    capability_id: str
    capability_name: str
    provider: ProviderType
    action_type: str
    risk_level_default: RiskLevel
    constraints: dict[str, Any]


class AgentResponse(BaseModel):
    """Agent response model with capability grants."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    agent_type: str
    description: str | None
    status: AgentStatus
    metadata: dict[str, Any]
    quarantine_reason: str | None
    capabilities: list[CapabilityGrantResponse]
