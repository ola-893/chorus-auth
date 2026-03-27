"""
Deterministic policy evaluation for delegated action requests.
"""
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.enums import AgentStatus, ConnectedAccountStatus, EnforcementDecision, ProviderType
from ..db.models import Agent, AgentCapabilityGrant, Capability, ConnectedAccount, User


@dataclass
class PolicyEvaluation:
    """Result of deterministic policy checks."""

    allowed: bool
    decision: EnforcementDecision
    reason: str
    capability: Capability | None = None
    connected_account: ConnectedAccount | None = None
    matched_grant: AgentCapabilityGrant | None = None


class PolicyEngine:
    """Validate capability grants, provider access, and deterministic constraints."""

    def evaluate(
        self,
        session: Session,
        user: User,
        agent: Agent,
        provider: ProviderType,
        capability_name: str,
        payload: dict[str, Any],
    ) -> PolicyEvaluation:
        if agent.status == AgentStatus.QUARANTINED:
            return PolicyEvaluation(
                allowed=False,
                decision=EnforcementDecision.QUARANTINE,
                reason="Agent is quarantined and cannot execute actions.",
            )

        capability = session.scalar(
            select(Capability).where(
                Capability.name == capability_name,
                Capability.provider == provider,
            )
        )
        if capability is None:
            return PolicyEvaluation(
                allowed=False,
                decision=EnforcementDecision.BLOCK,
                reason="Requested capability is not registered for this provider.",
            )

        grant = session.scalar(
            select(AgentCapabilityGrant).where(
                AgentCapabilityGrant.agent_id == agent.id,
                AgentCapabilityGrant.capability_id == capability.id,
            )
        )
        if grant is None:
            return PolicyEvaluation(
                allowed=False,
                decision=EnforcementDecision.BLOCK,
                reason="Agent does not have the requested capability grant.",
                capability=capability,
            )

        connected_account = session.scalar(
            select(ConnectedAccount).where(
                ConnectedAccount.user_id == user.id,
                ConnectedAccount.provider == provider,
                ConnectedAccount.status == ConnectedAccountStatus.CONNECTED,
            )
        )
        if connected_account is None:
            return PolicyEvaluation(
                allowed=False,
                decision=EnforcementDecision.BLOCK,
                reason="No connected account is available for the requested provider.",
                capability=capability,
                matched_grant=grant,
            )

        constraint_violation = self._validate_constraints(capability.name, grant.constraints_json, payload)
        if constraint_violation:
            return PolicyEvaluation(
                allowed=False,
                decision=EnforcementDecision.BLOCK,
                reason=constraint_violation,
                capability=capability,
                connected_account=connected_account,
                matched_grant=grant,
            )

        return PolicyEvaluation(
            allowed=True,
            decision=EnforcementDecision.ALLOW,
            reason="Capability grant and provider access validated.",
            capability=capability,
            connected_account=connected_account,
            matched_grant=grant,
        )

    def _validate_constraints(
        self,
        capability_name: str,
        constraints: dict[str, Any],
        payload: dict[str, Any],
    ) -> str | None:
        if not constraints:
            return None

        if capability_name == "gmail.draft.create":
            allowed_domains = constraints.get("allowed_domains")
            recipients = payload.get("to", [])
            if allowed_domains and recipients:
                invalid = [
                    email
                    for email in recipients
                    if "@" in email and email.split("@", 1)[1] not in set(allowed_domains)
                ]
                if invalid:
                    return f"Recipients violate allowed domain constraint: {', '.join(invalid)}"

        if capability_name in {"github.issue.create", "github.pull_request.merge"}:
            allowed_repo = constraints.get("repo")
            requested_repo = payload.get("repository")
            if allowed_repo and requested_repo and allowed_repo != requested_repo:
                return f"Requested repository '{requested_repo}' is outside the granted repository scope."

        return None
