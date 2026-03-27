"""
Vault adapter implementations for delegated provider access.
"""
from dataclasses import dataclass
from typing import Protocol

from ..control_plane_config import settings
from ..db.enums import ProviderType
from ..db.models import User


@dataclass
class ProviderAccess:
    """Normalized vault access metadata."""

    provider: str
    scope_count: int
    reference: str
    mode: str


class VaultAdapter(Protocol):
    """Protocol for provider access lookup."""

    def get_provider_access(self, user: User, provider: ProviderType, scopes: list[str]) -> ProviderAccess:
        """Return normalized provider access metadata."""


class MockVaultAdapter:
    """Mock vault adapter for demo mode."""

    def get_provider_access(self, user: User, provider: ProviderType, scopes: list[str]) -> ProviderAccess:
        return ProviderAccess(
            provider=provider.value,
            scope_count=len(scopes),
            reference=f"mock://{provider.value}/{user.id}",
            mode="mock",
        )


class TokenVaultAdapter:
    """Placeholder Token Vault adapter for future live integration."""

    def get_provider_access(self, user: User, provider: ProviderType, scopes: list[str]) -> ProviderAccess:
        return ProviderAccess(
            provider=provider.value,
            scope_count=len(scopes),
            reference=f"token-vault://{provider.value}/{user.id}",
            mode=settings.vault_mode,
        )


def get_vault_adapter() -> VaultAdapter:
    """Return the configured vault adapter."""
    if settings.vault_mode == "live":
        return TokenVaultAdapter()
    return MockVaultAdapter()
