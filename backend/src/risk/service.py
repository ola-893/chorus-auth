"""
Risk scoring for delegated action requests.
"""
from dataclasses import dataclass
from typing import Any

from ..db.enums import EnforcementDecision, RiskLevel
from ..db.models import Agent, Capability
from .gemini_adapter import GeminiRiskAdapter


@dataclass
class RiskAssessmentResult:
    """Normalized risk analysis output."""

    score: float
    level: RiskLevel
    explanation: str
    recommendation: EnforcementDecision
    source: str
    confidence: float


class RiskEngine:
    """Combine deterministic risk scoring with optional Gemini context."""

    def __init__(self) -> None:
        self.gemini = GeminiRiskAdapter()

    def assess(
        self,
        agent: Agent,
        capability: Capability,
        payload: dict[str, Any],
        policy_reason: str,
    ) -> RiskAssessmentResult:
        score, level, recommendation = self._score_for_capability(capability.name, payload)
        explanation = self._base_explanation(agent.name, capability.name, level)
        source = "rules"

        gemini_explanation = self.gemini.explain(
            provider=capability.provider.value,
            capability_name=capability.name,
            payload=payload,
            policy_reason=policy_reason,
        )
        if gemini_explanation:
            explanation = f"{explanation} Gemini note: {gemini_explanation}"
            source = "rules+gemini"

        return RiskAssessmentResult(
            score=score,
            level=level,
            explanation=explanation,
            recommendation=recommendation,
            source=source,
            confidence=0.85 if source == "rules+gemini" else 0.7,
        )

    def _score_for_capability(
        self,
        capability_name: str,
        payload: dict[str, Any],
    ) -> tuple[float, RiskLevel, EnforcementDecision]:
        if capability_name == "gmail.draft.create":
            return 0.2, RiskLevel.LOW, EnforcementDecision.ALLOW

        if capability_name == "github.issue.create":
            return 0.55, RiskLevel.MEDIUM, EnforcementDecision.REQUIRE_APPROVAL

        if capability_name == "github.pull_request.merge":
            score = 0.92 if payload.get("branch") == "main" else 0.85
            return score, RiskLevel.HIGH, EnforcementDecision.BLOCK

        return 0.5, RiskLevel.MEDIUM, EnforcementDecision.REQUIRE_APPROVAL

    def _base_explanation(
        self,
        agent_name: str,
        capability_name: str,
        level: RiskLevel,
    ) -> str:
        return (
            f"{agent_name} requested {capability_name}, which is classified as "
            f"{level.value} risk under the current MVP rules."
        )
