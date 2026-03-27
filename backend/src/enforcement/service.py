"""
Final decision mapping for policy and risk outputs.
"""
from dataclasses import dataclass

from ..control_plane_config import settings
from ..db.enums import EnforcementDecision
from ..policy.service import PolicyEvaluation
from ..risk.service import RiskAssessmentResult


@dataclass
class EnforcementResult:
    """Final enforcement outcome."""

    decision: EnforcementDecision
    reason: str


class EnforcementEngine:
    """Combine policy and risk outputs into a single control decision."""

    def decide(
        self,
        policy_result: PolicyEvaluation,
        risk_result: RiskAssessmentResult | None = None,
        blocked_violation_count: int = 0,
    ) -> EnforcementResult:
        if not policy_result.allowed:
            if (
                policy_result.decision == EnforcementDecision.BLOCK
                and blocked_violation_count >= settings.quarantine_after_blocked_requests
            ):
                return EnforcementResult(
                    decision=EnforcementDecision.QUARANTINE,
                    reason="Repeated blocked requests crossed the quarantine threshold.",
                )
            return EnforcementResult(
                decision=policy_result.decision,
                reason=policy_result.reason,
            )

        if risk_result is None:
            return EnforcementResult(
                decision=EnforcementDecision.ALLOW,
                reason=policy_result.reason,
            )

        if (
            risk_result.recommendation == EnforcementDecision.BLOCK
            and blocked_violation_count >= settings.quarantine_after_blocked_requests
        ):
            return EnforcementResult(
                decision=EnforcementDecision.QUARANTINE,
                reason="Repeated blocked requests crossed the quarantine threshold.",
            )

        return EnforcementResult(
            decision=risk_result.recommendation,
            reason=risk_result.explanation,
        )
