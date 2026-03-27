
import pytest
from unittest.mock import MagicMock
from datetime import datetime
from src.prediction_engine.impact_calculator import ImpactCalculator
from src.prediction_engine.models.alert import ClassifiedAlert, AlertSeverity, ImpactAssessment, AlertContext
from src.prediction_engine.models.core import ConflictAnalysis

class TestPropertyImpactMeasurement:
    """
    Property 6: Impact measurement accuracy.
    Validates: Requirements 4.2, 9.3
    """

    def test_impact_calculation_accuracy(self):
        """Verify downtime and cost savings calculations are deterministic."""
        calc = ImpactCalculator()
        
        # Test Case 1: Critical alert (60 mins downtime)
        analysis = ConflictAnalysis(
            risk_score=0.95,
            confidence_level=0.9,
            affected_agents=["a1", "a2"],
            predicted_failure_mode="Critical",
            nash_equilibrium=None,
            timestamp=datetime.now()
        )
        
        impact = calc.calculate_potential_impact(analysis)
        assert impact.estimated_downtime_minutes == 60
        
        # Test Case 2: Warning (5 mins downtime)
        analysis.risk_score = 0.5
        impact = calc.calculate_potential_impact(analysis)
        assert impact.estimated_downtime_minutes == 5

    def test_roi_accumulation(self):
        """Verify ROI metrics accumulate correctly over multiple interventions."""
        calc = ImpactCalculator()
        calc.metrics.hourly_downtime_cost = 6000.0 # $100/min for easy math
        
        # Alert 1: 60 mins -> $6000
        alert1 = ClassifiedAlert(
            severity=AlertSeverity.CRITICAL,
            title="A1",
            description="D1",
            impact=ImpactAssessment(0.9, 0.9, 60, [], ""),
            recommended_action="",
            requires_voice_alert=False,
            context=MagicMock(),
            timestamp=datetime.now()
        )
        
        calc.record_intervention(alert1, success=True)
        assert calc.metrics.total_cost_savings_usd == 6000.0
        
        # Alert 2: 30 mins -> $3000
        alert2 = ClassifiedAlert(
            severity=AlertSeverity.WARNING,
            title="A2",
            description="D2",
            impact=ImpactAssessment(0.5, 0.5, 30, [], ""),
            recommended_action="",
            requires_voice_alert=False,
            context=MagicMock(),
            timestamp=datetime.now()
        )
        
        calc.record_intervention(alert2, success=True)
        assert calc.metrics.total_cost_savings_usd == 9000.0
        assert calc.metrics.total_prevented_downtime_minutes == 90
        assert calc.metrics.intervention_count == 2
