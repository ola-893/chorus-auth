"""
Provider adapter protocol and execution result models.
"""
from dataclasses import dataclass
from typing import Protocol

from ..vault.adapters import ProviderAccess


@dataclass
class ProviderExecutionResult:
    """Normalized provider execution result."""

    success: bool
    summary: str
    external_reference_id: str
    payload: dict


class ProviderAdapter(Protocol):
    """Protocol for provider adapters."""

    def execute(
        self,
        capability_name: str,
        payload: dict,
        access: ProviderAccess,
    ) -> ProviderExecutionResult:
        """Execute a provider action."""
