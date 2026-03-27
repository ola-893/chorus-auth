
import pytest
from hypothesis import given, strategies as st
from datetime import datetime

from src.prediction_engine.voice_script_generator import VoiceScriptGenerator
from src.prediction_engine.models.alert import ClassifiedAlert, AlertSeverity, AlertContext, ImpactAssessment

class TestPropertyScriptGeneration:
    
    def _create_mock_alert(self, severity, risk_score):
        impact = ImpactAssessment(
            system_impact_score=risk_score,
            business_impact_score=risk_score,
            estimated_downtime_minutes=10,
            affected_services=[],
            description="Test impact"
        )
        context = AlertContext(
            incident_type="test",
            affected_agents=["agent1", "agent2"],
            risk_score=risk_score,
            timestamp=datetime.now()
        )
        return ClassifiedAlert(
            severity=severity,
            title="TEST: Failure Mode X",
            description="Test description",
            impact=impact,
            recommended_action="Do nothing",
            requires_voice_alert=True,
            context=context,
            timestamp=datetime.now()
        )

    @given(st.sampled_from([AlertSeverity.CRITICAL, AlertSeverity.WARNING]))
    def test_contextual_script_accuracy(self, severity):
        """
        Property 3: Contextual script generation accuracy.
        Generated scripts must contain key context variables like risk score or agent count.
        """
        generator = VoiceScriptGenerator()
        alert = self._create_mock_alert(severity, 0.9 if severity == AlertSeverity.CRITICAL else 0.5)
        
        script = generator.generate_script(alert, audience="technical")
        
        # Verify key information is present
        assert "2" in script # agent_count
        
        if severity == AlertSeverity.CRITICAL:
            assert "0.90" in script # risk score formatted
            assert "Failure Mode X" in script
        elif severity == AlertSeverity.WARNING:
            assert "Warning" in script

    def test_template_fallback(self):
        """Test fallback to default template."""
        generator = VoiceScriptGenerator()
        # Create an alert that maps to a missing template key
        alert = self._create_mock_alert(AlertSeverity.INFO, 0.1)
        
        script = generator.generate_script(alert, audience="technical")
        
        # Should use default template
        assert "Alert received" in script
        assert "info" in script
