"""
Alert severity classification and impact assessment engine.
"""
import logging
from datetime import datetime
from typing import List, Dict, Optional

from .models.alert import AlertSeverity, AlertContext, ImpactAssessment, ClassifiedAlert
from .models.core import ConflictAnalysis
from .trust_manager import trust_manager
from .quarantine_manager import quarantine_manager
from ..config import settings
from ..logging_config import get_agent_logger

agent_logger = get_agent_logger(__name__)
logger = logging.getLogger(__name__)

class AlertSeverityClassifier:
    """
    Classifies incidents and determines alert severity based on configurable rules.
    """
    
    def __init__(self):
        self.trust_manager = trust_manager
        self.quarantine_manager = quarantine_manager
        
        # Default severity thresholds
        self.risk_thresholds = {
            AlertSeverity.INFO: 0.3,
            AlertSeverity.WARNING: 0.6,
            AlertSeverity.CRITICAL: 0.85,
            AlertSeverity.EMERGENCY: 0.95
        }
        
    def classify_conflict(self, analysis: ConflictAnalysis) -> ClassifiedAlert:
        """
        Classify a conflict analysis result into an alert.
        """
        # Gather context
        active_quarantines = len(self.quarantine_manager.get_quarantined_agents())
        trust_trend = self._analyze_trust_trend(analysis.affected_agents)
        
        context = AlertContext(
            incident_type="conflict_prediction",
            affected_agents=analysis.affected_agents,
            risk_score=analysis.risk_score,
            active_quarantines=active_quarantines,
            trust_score_trend=trust_trend,
            timestamp=datetime.now()
        )
        
        # Determine severity
        severity = self._determine_severity(context)
        
        # Assess impact
        impact = self._assess_impact(context, severity)
        
        # Determine if voice alert is needed
        requires_voice = severity in [AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY]
        
        return ClassifiedAlert(
            severity=severity,
            title=f"{severity.value.upper()}: {analysis.predicted_failure_mode}",
            description=f"Detected high-risk conflict involving {len(analysis.affected_agents)} agents.",
            impact=impact,
            recommended_action=self._get_recommendation(severity, context),
            requires_voice_alert=requires_voice,
            context=context,
            timestamp=datetime.now()
        )

    def _determine_severity(self, context: AlertContext) -> AlertSeverity:
        """Determine severity level based on context."""
        # Escalation logic for multiple quarantines
        if context.active_quarantines >= 3 and context.risk_score > 0.5:
            return AlertSeverity.EMERGENCY
            
        # Escalation for degrading trust
        if context.trust_score_trend == "degrading" and context.risk_score > 0.7:
            return AlertSeverity.CRITICAL
            
        # Base risk score mapping
        if context.risk_score >= self.risk_thresholds[AlertSeverity.EMERGENCY]:
            return AlertSeverity.EMERGENCY
        elif context.risk_score >= self.risk_thresholds[AlertSeverity.CRITICAL]:
            return AlertSeverity.CRITICAL
        elif context.risk_score >= self.risk_thresholds[AlertSeverity.WARNING]:
            return AlertSeverity.WARNING
        else:
            return AlertSeverity.INFO

    def _assess_impact(self, context: AlertContext, severity: AlertSeverity) -> ImpactAssessment:
        """Calculate business and system impact."""
        # Placeholder logic for impact calculation
        base_impact = context.risk_score
        agent_factor = len(context.affected_agents) * 0.1
        
        system_impact = min(1.0, base_impact + agent_factor)
        business_impact = min(1.0, system_impact * 0.8) # Assuming some redundancy
        
        services = ["AgentNetwork"]
        if severity in [AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY]:
            services.append("TransactionProcessing")
            
        return ImpactAssessment(
            system_impact_score=system_impact,
            business_impact_score=business_impact,
            estimated_downtime_minutes=int(system_impact * 60),
            affected_services=services,
            description="Potential degradation of agent coordination services."
        )

    def _analyze_trust_trend(self, agents: List[str]) -> str:
        """Analyze trust score trend for affected agents."""
        if not agents:
            return "stable"
            
        degrading_count = 0
        for agent_id in agents:
            analytics = self.trust_manager.get_trust_score_analytics(agent_id)
            if analytics.get("trend", 0) < -0.5:
                degrading_count += 1
        
        if degrading_count > len(agents) / 2:
            return "degrading"
        return "stable"

    def _get_recommendation(self, severity: AlertSeverity, context: AlertContext) -> str:
        """Get recommended action based on severity."""
        if severity == AlertSeverity.EMERGENCY:
            return "Immediate manual intervention required. Consider system pause."
        elif severity == AlertSeverity.CRITICAL:
            return "Review automated quarantines and monitor closely."
        elif severity == AlertSeverity.WARNING:
            return "Monitor flagged agents for escalation."
        return "No immediate action required."

# Global instance
severity_classifier = AlertSeverityClassifier()
