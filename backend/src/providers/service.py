"""
Mock-first provider adapters and registry.
"""
from uuid import uuid4

from ..db.enums import ProviderType
from ..vault.adapters import ProviderAccess
from .base import ProviderAdapter, ProviderExecutionResult


class GmailProviderAdapter:
    """Mock Gmail adapter."""

    def execute(
        self,
        capability_name: str,
        payload: dict,
        access: ProviderAccess,
    ) -> ProviderExecutionResult:
        recipients = payload.get("to", [])
        draft_id = f"draft-{uuid4()}"
        return ProviderExecutionResult(
            success=True,
            summary=f"Created Gmail draft for {len(recipients)} recipient(s).",
            external_reference_id=draft_id,
            payload={
                "draft_id": draft_id,
                "recipient_count": len(recipients),
                "vault_reference": access.reference,
            },
        )


class GitHubProviderAdapter:
    """Mock GitHub adapter."""

    def execute(
        self,
        capability_name: str,
        payload: dict,
        access: ProviderAccess,
    ) -> ProviderExecutionResult:
        reference_id = f"github-{uuid4()}"
        repository = payload.get("repository", "unknown")
        action_label = "issue" if capability_name == "github.issue.create" else "pull request action"
        return ProviderExecutionResult(
            success=True,
            summary=f"Created {action_label} event for {repository}.",
            external_reference_id=reference_id,
            payload={
                "repository": repository,
                "reference_id": reference_id,
                "vault_reference": access.reference,
            },
        )


class ProviderRegistry:
    """Lookup provider adapters by provider type."""

    def __init__(self) -> None:
        self._providers: dict[ProviderType, ProviderAdapter] = {
            ProviderType.GMAIL: GmailProviderAdapter(),
            ProviderType.GITHUB: GitHubProviderAdapter(),
        }

    def get(self, provider: ProviderType) -> ProviderAdapter:
        return self._providers[provider]


provider_registry = ProviderRegistry()
