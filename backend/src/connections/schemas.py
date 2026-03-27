"""
Pydantic schemas for connected account APIs.
"""
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..db.enums import ConnectedAccountStatus, ProviderType


class ConnectedAccountCreate(BaseModel):
    """Request model for creating or updating a connected account."""

    provider: ProviderType
    external_account_id: str | None = None
    scopes: list[str] = Field(default_factory=list)
    status: ConnectedAccountStatus = ConnectedAccountStatus.CONNECTED
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectedAccountResponse(BaseModel):
    """Response model for connected accounts."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    provider: ProviderType
    external_account_id: str | None
    scopes: list[str]
    status: ConnectedAccountStatus
    connection_mode: str
    vault_reference: str
