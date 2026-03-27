"""
Vault adapter implementations for delegated provider access.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from secrets import token_urlsafe
from typing import Any, Protocol

import httpx
from fastapi import HTTPException, status

from ..control_plane_config import settings
from ..db.enums import ConnectionHealthStatus, ProviderType
from ..db.models import User


@dataclass
class ProviderAccess:
    """Normalized vault access metadata."""

    provider: str
    scope_count: int
    reference: str
    mode: str
    access_token: str | None = None
    granted_scopes: list[str] | None = None
    external_account_id: str | None = None


@dataclass
class ConnectionStartResult:
    """Connection-start payload returned to the UI."""

    provider: ProviderType
    mode: str
    authorization_url: str | None
    state: str
    auth_session: str | None
    redirect_uri: str
    requested_scopes: list[str]
    message: str


@dataclass
class ConnectionSyncResult:
    """Normalized connection details returned after completion or refresh."""

    provider: ProviderType
    mode: str
    external_account_id: str | None
    display_label: str
    granted_scopes: list[str]
    vault_reference: str
    connection_health: ConnectionHealthStatus
    metadata: dict[str, Any]
    last_synced_at: datetime


class VaultAdapter(Protocol):
    """Protocol for provider access lookup and connection flows."""

    def get_provider_access(
        self,
        user: User,
        provider: ProviderType,
        scopes: list[str],
        subject_token: str | None = None,
    ) -> ProviderAccess:
        """Return normalized provider access metadata."""

    def start_connection(
        self,
        user: User,
        provider: ProviderType,
        redirect_uri: str,
        requested_scopes: list[str],
        my_account_token: str | None = None,
    ) -> ConnectionStartResult:
        """Begin a provider connection flow."""

    def complete_connection(
        self,
        user: User,
        provider: ProviderType,
        auth_session: str,
        connect_code: str,
        redirect_uri: str,
        my_account_token: str | None = None,
    ) -> ConnectionSyncResult:
        """Complete a provider connection callback."""

    def refresh_connection(
        self,
        user: User,
        provider: ProviderType,
        external_account_id: str | None,
        my_account_token: str | None = None,
    ) -> ConnectionSyncResult:
        """Refresh connection metadata from the source of truth."""


class MockVaultAdapter:
    """Mock vault adapter for demo mode."""

    def get_provider_access(
        self,
        user: User,
        provider: ProviderType,
        scopes: list[str],
        subject_token: str | None = None,
    ) -> ProviderAccess:
        del subject_token
        return ProviderAccess(
            provider=provider.value,
            scope_count=len(scopes),
            reference=f"mock://{provider.value}/{user.id}",
            mode="mock",
            granted_scopes=list(scopes),
        )

    def start_connection(
        self,
        user: User,
        provider: ProviderType,
        redirect_uri: str,
        requested_scopes: list[str],
        my_account_token: str | None = None,
    ) -> ConnectionStartResult:
        del user, my_account_token
        return ConnectionStartResult(
            provider=provider,
            mode="mock",
            authorization_url=None,
            state=token_urlsafe(24),
            auth_session=f"mock-session-{provider.value}",
            redirect_uri=redirect_uri,
            requested_scopes=requested_scopes or default_scopes_for_provider(provider),
            message="Mock connection flow initialized locally.",
        )

    def complete_connection(
        self,
        user: User,
        provider: ProviderType,
        auth_session: str,
        connect_code: str,
        redirect_uri: str,
        my_account_token: str | None = None,
    ) -> ConnectionSyncResult:
        del auth_session, connect_code, redirect_uri, my_account_token
        return ConnectionSyncResult(
            provider=provider,
            mode="mock",
            external_account_id=f"demo-{provider.value}-account",
            display_label=default_label_for_provider(provider),
            granted_scopes=default_scopes_for_provider(provider),
            vault_reference=f"mock://{provider.value}/{user.id}",
            connection_health=ConnectionHealthStatus.HEALTHY,
            metadata={"source": "mock-token-vault"},
            last_synced_at=datetime.now(timezone.utc),
        )

    def refresh_connection(
        self,
        user: User,
        provider: ProviderType,
        external_account_id: str | None,
        my_account_token: str | None = None,
    ) -> ConnectionSyncResult:
        del external_account_id, my_account_token
        return ConnectionSyncResult(
            provider=provider,
            mode="mock",
            external_account_id=f"demo-{provider.value}-account",
            display_label=default_label_for_provider(provider),
            granted_scopes=default_scopes_for_provider(provider),
            vault_reference=f"mock://{provider.value}/{user.id}",
            connection_health=ConnectionHealthStatus.HEALTHY,
            metadata={"source": "mock-token-vault", "refreshed": True},
            last_synced_at=datetime.now(timezone.utc),
        )


class TokenVaultAdapter:
    """Auth0 Token Vault integration helpers for connection flows."""

    def get_provider_access(
        self,
        user: User,
        provider: ProviderType,
        scopes: list[str],
        subject_token: str | None = None,
    ) -> ProviderAccess:
        token = require_live_token(subject_token)
        payload = {
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "requested_token_type": "http://auth0.com/oauth/token-type/federated-connection-access-token",
            "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
            "subject_token": token,
            "connection": provider_connection_name(provider),
        }
        if settings.token_vault_audience:
            payload["audience"] = settings.token_vault_audience
        if settings.token_vault_client_id:
            payload["client_id"] = settings.token_vault_client_id
        if settings.token_vault_client_secret:
            payload["client_secret"] = settings.token_vault_client_secret
        with httpx.Client(timeout=settings.token_vault_timeout_seconds) as client:
            response = client.post(oauth_token_url(), data=payload)
        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Token Vault token exchange failed: {response.text}",
            )
        body = response.json()
        granted_scopes = body.get("scope", "")
        normalized_scopes = granted_scopes.split(" ") if granted_scopes else list(scopes)
        return ProviderAccess(
            provider=provider.value,
            scope_count=len(scopes),
            reference=f"token-vault://{provider.value}/{user.id}",
            mode=settings.vault_mode,
            access_token=body.get("access_token"),
            granted_scopes=normalized_scopes,
            external_account_id=body.get("external_account_id"),
        )

    def start_connection(
        self,
        user: User,
        provider: ProviderType,
        redirect_uri: str,
        requested_scopes: list[str],
        my_account_token: str | None = None,
    ) -> ConnectionStartResult:
        del user
        token = require_live_token(my_account_token)
        state = token_urlsafe(24)
        payload: dict[str, Any] = {
            "connection": provider_connection_name(provider),
            "redirect_uri": redirect_uri,
            "state": state,
        }
        if requested_scopes:
            payload["scopes"] = requested_scopes
        response = self._post("/connect", token, payload)
        authorization_url = response.get("connect_uri") or response.get("authorization_url")
        if authorization_url is None:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Token Vault did not return a connection URL",
            )
        return ConnectionStartResult(
            provider=provider,
            mode="live",
            authorization_url=str(authorization_url),
            state=str(response.get("state") or state),
            auth_session=response.get("auth_session"),
            redirect_uri=redirect_uri,
            requested_scopes=requested_scopes or default_scopes_for_provider(provider),
            message="Live Token Vault connection flow started.",
        )

    def complete_connection(
        self,
        user: User,
        provider: ProviderType,
        auth_session: str,
        connect_code: str,
        redirect_uri: str,
        my_account_token: str | None = None,
    ) -> ConnectionSyncResult:
        token = require_live_token(my_account_token)
        self._post(
            "/complete",
            token,
            {
                "auth_session": auth_session,
                "connect_code": connect_code,
                "redirect_uri": redirect_uri,
            },
        )
        return self.refresh_connection(user, provider, external_account_id=None, my_account_token=token)

    def refresh_connection(
        self,
        user: User,
        provider: ProviderType,
        external_account_id: str | None,
        my_account_token: str | None = None,
    ) -> ConnectionSyncResult:
        token = require_live_token(my_account_token)
        connections_payload = self._get("/connections", token)
        candidate = self._select_connection(connections_payload, provider, external_account_id)
        if candidate is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Connected account could not be found in Token Vault",
            )
        granted_scopes = parse_granted_scopes(candidate) or default_scopes_for_provider(provider)
        external_id = str(
            candidate.get("external_account_id")
            or candidate.get("account_id")
            or candidate.get("user_id")
            or external_account_id
            or f"{provider.value}-live-account"
        )
        display_label = str(
            candidate.get("display_name")
            or candidate.get("label")
            or candidate.get("name")
            or default_label_for_provider(provider)
        )
        vault_reference = str(
            candidate.get("vault_reference")
            or candidate.get("connection_id")
            or candidate.get("id")
            or f"token-vault://{provider.value}/{user.id}"
        )
        health = ConnectionHealthStatus.HEALTHY
        if candidate.get("status") in {"pending", "authorizing"}:
            health = ConnectionHealthStatus.PENDING
        elif candidate.get("status") in {"error", "failed"}:
            health = ConnectionHealthStatus.ERROR
        elif candidate.get("status") in {"degraded"}:
            health = ConnectionHealthStatus.DEGRADED
        return ConnectionSyncResult(
            provider=provider,
            mode="live",
            external_account_id=external_id,
            display_label=display_label,
            granted_scopes=granted_scopes,
            vault_reference=vault_reference,
            connection_health=health,
            metadata={"source": "token-vault", "raw_connection": candidate},
            last_synced_at=datetime.now(timezone.utc),
        )

    def _post(self, path: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(timeout=settings.token_vault_timeout_seconds) as client:
            response = client.post(
                f"{token_vault_base_url()}{path}",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
            )
        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Token Vault request failed: {response.text}",
            )
        return response.json()

    def _get(self, path: str, token: str) -> dict[str, Any]:
        with httpx.Client(timeout=settings.token_vault_timeout_seconds) as client:
            response = client.get(
                f"{token_vault_base_url()}{path}",
                headers={"Authorization": f"Bearer {token}"},
            )
        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Token Vault request failed: {response.text}",
            )
        return response.json()

    def _select_connection(
        self,
        payload: dict[str, Any],
        provider: ProviderType,
        external_account_id: str | None,
    ) -> dict[str, Any] | None:
        items = payload.get("connections") or payload.get("connected_accounts") or payload.get("accounts") or []
        connection_name = provider_connection_name(provider)
        for item in items:
            if item.get("connection") == connection_name or item.get("provider") == provider.value:
                if external_account_id is None or item.get("external_account_id") == external_account_id:
                    return item
        return None


def get_vault_adapter() -> VaultAdapter:
    """Return the configured vault adapter."""
    if settings.vault_mode == "live":
        return TokenVaultAdapter()
    return MockVaultAdapter()


def provider_connection_name(provider: ProviderType) -> str:
    """Return the configured Token Vault connection name for a provider."""
    mapping = {
        ProviderType.GMAIL: settings.token_vault_google_connection,
        ProviderType.GITHUB: settings.token_vault_github_connection,
    }
    return mapping[provider]


def default_scopes_for_provider(provider: ProviderType) -> list[str]:
    """Return demo-safe default scopes by provider."""
    if provider == ProviderType.GMAIL:
        return ["gmail.compose", "gmail.readonly"]
    return ["repo", "issues:write", "pull_requests:write"]


def default_label_for_provider(provider: ProviderType) -> str:
    """Return a user-facing connection label."""
    if provider == ProviderType.GMAIL:
        return "Google Workspace Mailbox"
    return "GitHub Repository Access"


def token_vault_base_url() -> str:
    """Return the Token Vault connected-account base URL."""
    if settings.token_vault_base_url:
        return settings.token_vault_base_url.rstrip("/")
    if settings.auth0_issuer:
        return f"{settings.auth0_issuer.rstrip('/')}/me/v1/connected-accounts"
    if settings.auth0_domain:
        domain = settings.auth0_domain.rstrip("/")
        if not domain.startswith("http"):
            domain = f"https://{domain}"
        return f"{domain}/me/v1/connected-accounts"
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Token Vault base URL is not configured",
    )


def oauth_token_url() -> str:
    """Return the Auth0 OAuth token URL for token exchange."""
    if settings.auth0_issuer:
        return f"{settings.auth0_issuer.rstrip('/')}/oauth/token"
    if settings.auth0_domain:
        domain = settings.auth0_domain.rstrip("/")
        if not domain.startswith("http"):
            domain = f"https://{domain}"
        return f"{domain}/oauth/token"
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Auth0 domain is not configured for Token Vault token exchange",
    )


def require_live_token(token: str | None) -> str:
    """Require a My Account API token for live Token Vault operations."""
    if token:
        return token
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="A My Account API token is required for live Token Vault operations",
    )


def parse_granted_scopes(payload: dict[str, Any]) -> list[str]:
    """Normalize scopes from a Token Vault connection payload."""
    scopes = payload.get("scopes") or payload.get("granted_scopes") or []
    if isinstance(scopes, str):
        return [item for item in scopes.split(" ") if item]
    return [str(item) for item in scopes]
