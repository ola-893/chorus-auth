"""
Connected account persistence and Token Vault lifecycle helpers.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..control_plane_config import settings
from ..db.enums import ConnectedAccountStatus, ConnectionHealthStatus
from ..db.models import ConnectedAccount, User
from ..realtime.events import publish_dashboard_event
from ..vault.adapters import get_vault_adapter
from .schemas import (
    ConnectedAccountCreate,
    ConnectedAccountResponse,
    ConnectionCallbackResponse,
    ConnectionRefreshRequest,
    ConnectionStartRequest,
    ConnectionStartResponse,
)


def serialize_connected_account(user: User, account: ConnectedAccount) -> ConnectedAccountResponse:
    """Convert an account record into an API response."""
    return ConnectedAccountResponse(
        id=account.id,
        provider=account.provider,
        external_account_id=account.external_account_id,
        display_label=account.display_label,
        scopes=list(account.scopes_json),
        granted_scopes=list(account.scopes_json),
        status=account.status,
        connection_health=account.connection_health,
        connection_mode=account.connection_mode,
        mode=account.connection_mode,
        vault_reference=account.vault_reference or f"{account.connection_mode}://{account.provider.value}/{user.id}",
        last_synced_at=account.last_synced_at,
    )


def list_connections(session: Session, user: User) -> list[ConnectedAccountResponse]:
    """Return all connections for the user."""
    accounts = session.scalars(
        select(ConnectedAccount)
        .where(ConnectedAccount.user_id == user.id)
        .order_by(ConnectedAccount.created_at.asc())
    ).all()
    return [serialize_connected_account(user, account) for account in accounts]


def create_or_update_connection(
    session: Session,
    user: User,
    payload: ConnectedAccountCreate,
) -> ConnectedAccountResponse:
    """Create or update a connected account for the user."""
    account = _get_or_create_account(session, user, payload.provider)
    account.external_account_id = payload.external_account_id
    account.display_label = payload.display_label or account.display_label
    account.scopes_json = payload.scopes
    account.status = payload.status
    account.connection_health = ConnectionHealthStatus.HEALTHY
    account.connection_mode = settings.vault_mode
    account.vault_reference = account.vault_reference or f"{settings.vault_mode}://{payload.provider.value}/{user.id}"
    account.last_synced_at = datetime.now(timezone.utc)
    account.metadata_json = payload.metadata

    session.commit()
    session.refresh(account)
    response = serialize_connected_account(user, account)
    publish_dashboard_event("connection.updated", response.model_dump(mode="json"))
    return response


def start_connection(
    session: Session,
    user: User,
    provider,
    payload: ConnectionStartRequest,
) -> ConnectionStartResponse:
    """Begin a Token Vault-backed provider connection flow."""
    del session
    result = get_vault_adapter().start_connection(
        user,
        provider,
        payload.redirect_uri,
        payload.requested_scopes,
        payload.my_account_token,
    )
    return ConnectionStartResponse(
        provider=result.provider,
        mode=result.mode,
        authorization_url=result.authorization_url,
        state=result.state,
        auth_session=result.auth_session,
        redirect_uri=result.redirect_uri,
        message=result.message,
    )


def complete_connection(
    session: Session,
    user: User,
    provider,
    *,
    auth_session: str,
    connect_code: str,
    redirect_uri: str,
    my_account_token: str | None,
) -> ConnectionCallbackResponse:
    """Complete a provider callback and persist the resulting connection."""
    result = get_vault_adapter().complete_connection(
        user,
        provider,
        auth_session,
        connect_code,
        redirect_uri,
        my_account_token,
    )
    account = _get_or_create_account(session, user, provider)
    _apply_connection_sync(account, user, result)

    session.commit()
    session.refresh(account)
    serialized = serialize_connected_account(user, account)
    publish_dashboard_event("connection.updated", serialized.model_dump(mode="json"))
    return ConnectionCallbackResponse(
        **serialized.model_dump(),
        message="Connected account is ready for delegated actions.",
    )


def refresh_connection(
    session: Session,
    user: User,
    connection_id: str,
    payload: ConnectionRefreshRequest,
) -> ConnectedAccountResponse:
    """Refresh a connection from the vault source of truth."""
    account = session.scalar(
        select(ConnectedAccount).where(
            ConnectedAccount.id == connection_id,
            ConnectedAccount.user_id == user.id,
        )
    )
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connected account not found")

    result = get_vault_adapter().refresh_connection(
        user,
        account.provider,
        account.external_account_id,
        payload.my_account_token,
    )
    _apply_connection_sync(account, user, result)
    session.commit()
    session.refresh(account)
    response = serialize_connected_account(user, account)
    publish_dashboard_event("connection.updated", response.model_dump(mode="json"))
    return response


def disconnect_connection(session: Session, user: User, connection_id: str) -> ConnectedAccountResponse:
    """Disconnect a provider account without deleting history."""
    account = session.scalar(
        select(ConnectedAccount).where(
            ConnectedAccount.id == connection_id,
            ConnectedAccount.user_id == user.id,
        )
    )
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connected account not found")
    account.status = ConnectedAccountStatus.DISCONNECTED
    account.connection_health = ConnectionHealthStatus.DEGRADED
    account.last_synced_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(account)
    response = serialize_connected_account(user, account)
    publish_dashboard_event("connection.updated", response.model_dump(mode="json"))
    return response


def _get_or_create_account(session: Session, user: User, provider) -> ConnectedAccount:
    account = session.scalar(
        select(ConnectedAccount).where(
            ConnectedAccount.user_id == user.id,
            ConnectedAccount.provider == provider,
        )
    )
    if account is None:
        account = ConnectedAccount(
            user_id=user.id,
            provider=provider,
            status=ConnectedAccountStatus.CONNECTED,
            connection_health=ConnectionHealthStatus.HEALTHY,
            connection_mode=settings.vault_mode,
            metadata_json={},
        )
        session.add(account)
    return account


def _apply_connection_sync(account: ConnectedAccount, user: User, result) -> None:
    account.external_account_id = result.external_account_id
    account.display_label = result.display_label
    account.scopes_json = result.granted_scopes
    account.status = ConnectedAccountStatus.CONNECTED
    account.connection_health = result.connection_health
    account.connection_mode = result.mode
    account.vault_reference = result.vault_reference or f"{result.mode}://{account.provider.value}/{user.id}"
    account.last_synced_at = result.last_synced_at
    account.metadata_json = result.metadata
