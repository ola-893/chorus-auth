"""
Business impact calculation and ROI analysis engine.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .models.alert import ClassifiedAlert, AlertSeverity, ImpactAssessment
from .models.core import ConflictAnalysis

logger = logging.getLogger(__name__)

@dataclass
class ImpactMetrics:
    """Aggregated business impact metrics."""
    total_prevented_downtime_minutes: float = 0.0
    total_cost_savings_usd: float = 0.0
    intervention_count: int = 0
    prevention_rate: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)
    
    # Cost basis
    hourly_downtime_cost: float = 10000.0 # Default $10k/hr
    hourly_agent_cost: float = 0.50 # Default $0.50/hr per agent

class ImpactCalculator:
    """
    Calculates business impact and ROI from system interventions.
    """
    
    def __init__(self):
        self.metrics = ImpactMetrics()
        self.incident_history: List[Dict] = []
        
    def calculate_potential_impact(self, analysis: ConflictAnalysis) -> ImpactAssessment:
        """
        Calculate potential impact of a predicted conflict if left unresolved.
        """
        # Base impact from risk score
        system_impact = analysis.risk_score
        
        # Business impact multiplier based on agent count and severity
        agent_factor = len(analysis.affected_agents) * 0.1
        business_impact = min(1.0, system_impact * (1.0 + agent_factor))
        
        # Estimate potential downtime based on severity
        if system_impact > 0.9:
            downtime = 60 # Critical failure
        elif system_impact > 0.7:
            downtime = 15 # Major degradation
        elif system_impact > 0.4:
            downtime = 5  # Minor glitch
        else:
            downtime = 0
            
        description = f"Potential {downtime}m downtime affecting {len(analysis.affected_agents)} agents."
        
        return ImpactAssessment(
            system_impact_score=system_impact,
            business_impact_score=business_impact,
            estimated_downtime_minutes=downtime,
            affected_services=["agent_network"], # Placeholder
            description=description
        )

    def record_intervention(self, alert: ClassifiedAlert, success: bool = True):
        """
        Record a successful intervention and update ROI metrics.
        """
        if not success:
            return

        impact = alert.impact
        if not impact:
            return

        # Calculate savings
        savings = (impact.estimated_downtime_minutes / 60.0) * self.metrics.hourly_downtime_cost
        
        # Update metrics
        self.metrics.total_prevented_downtime_minutes += impact.estimated_downtime_minutes
        self.metrics.total_cost_savings_usd += savings
        self.metrics.intervention_count += 1
        self.metrics.last_updated = datetime.now()
        
        # Update prevention rate (simplified)
        self.metrics.prevention_rate = 0.99 # Mock high rate for demo
        
        # Log history
        self.incident_history.append({
            "timestamp": datetime.now(),
            "alert_title": alert.title,
            "severity": alert.severity.value,
            "savings": savings,
            "downtime_prevented": impact.estimated_downtime_minutes
        })
        
        logger.info(f"Recorded intervention: ${savings:.2f} savings, {impact.estimated_downtime_minutes}m downtime prevented")

    def get_metrics(self) -> ImpactMetrics:
        return self.metrics

    def generate_roi_report(self) -> Dict:
        """Generate comprehensive ROI report."""
        return {
            "summary": {
                "total_savings": self.metrics.total_cost_savings_usd,
                "downtime_prevented_minutes": self.metrics.total_prevented_downtime_minutes,
                "interventions": self.metrics.intervention_count,
                "roi_multiplier": "15x" # Mock ROI
            },
            "history": self.incident_history[-10:] # Last 10
        }

# Global instance
impact_calculator = ImpactCalculator()
