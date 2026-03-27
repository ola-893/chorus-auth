"""
Pydantic schemas for connected account APIs.
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..db.enums import ConnectedAccountStatus, ConnectionHealthStatus, ProviderType


class ConnectedAccountCreate(BaseModel):
    """Request model for creating or updating a connected account."""

    provider: ProviderType
    external_account_id: str | None = None
    display_label: str | None = None
    scopes: list[str] = Field(default_factory=list)
    status: ConnectedAccountStatus = ConnectedAccountStatus.CONNECTED
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectedAccountResponse(BaseModel):
    """Response model for connected accounts."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    provider: ProviderType
    external_account_id: str | None
    display_label: str | None
    scopes: list[str]
    granted_scopes: list[str]
    status: ConnectedAccountStatus
    connection_health: ConnectionHealthStatus
    connection_mode: str
    mode: str
    vault_reference: str
    last_synced_at: datetime | None


class ConnectionStartRequest(BaseModel):
    """Request body for beginning a provider connection flow."""

    redirect_uri: str
    requested_scopes: list[str] = Field(default_factory=list)
    my_account_token: str | None = None


class ConnectionStartResponse(BaseModel):
    """Serialized connection-start response."""

    provider: ProviderType
    mode: str
    authorization_url: str | None
    state: str
    auth_session: str | None
    redirect_uri: str
    message: str


class ConnectionRefreshRequest(BaseModel):
    """Refresh an existing connection from the live Token Vault source."""

    my_account_token: str | None = None


class ConnectionCallbackResponse(ConnectedAccountResponse):
    """Connected account response returned from a callback completion."""

    message: str
