
import pytest
from hypothesis import given, strategies as st
from datetime import datetime
from unittest.mock import patch

from src.prediction_engine.voice_script_generator import VoiceScriptGenerator
from src.prediction_engine.models.alert import ClassifiedAlert, AlertSeverity, AlertContext, ImpactAssessment

class TestPropertyAudienceNarration:
    
    def _create_mock_alert(self, title, risk_score):
        context = AlertContext(
            incident_type="demo",
            affected_agents=["agent1", "agent2", "agent3"],
            risk_score=risk_score,
            timestamp=datetime.now()
        )
        impact = ImpactAssessment(
            system_impact_score=risk_score,
            business_impact_score=risk_score,
            estimated_downtime_minutes=10,
            affected_services=[],
            description="Demo impact"
        )
        return ClassifiedAlert(
            severity=AlertSeverity.CRITICAL,
            title=title,
            description="Demo description",
            impact=impact,
            recommended_action="None",
            requires_voice_alert=True,
            context=context,
            timestamp=datetime.now()
        )

    def test_technical_narration_content(self):
        """
        Property 8: Audience-specific demo narration (Technical).
        Verify technical scripts contain game theory concepts.
        """
        generator = VoiceScriptGenerator()
        
        # We need to manually select the specific demo templates for this test
        # or mock the selection logic if we haven't updated _select_template yet.
        # Since _select_template uses standard logic, we might need to invoke render directly
        # or assume the user (DemoEngine) calls a specific method or we update _select_template.
        
        # For the DemoScenarioEngine, it likely asks for specific templates by name or context.
        # Let's test the template rendering directly to ensure the content is correct.
        
        alert = self._create_mock_alert("Demo", 0.95)
        context = generator._build_context(alert)
        
        # Test Technical Intro
        script_tech = generator.templates["technical_demo_info"].render(context)
        assert "Nash Equilibria" in script_tech
        assert "3" in script_tech # agent count
        
        # Test Technical Escalation
        script_esc = generator.templates["technical_demo_critical"].render(context)
        assert "Shapley values" in script_esc
        assert "0.95" in script_esc # risk score

    def test_business_narration_content(self):
        """
        Property 8: Audience-specific demo narration (Business).
        Verify business scripts focus on cost and uptime.
        """
        generator = VoiceScriptGenerator()
        alert = self._create_mock_alert("Demo", 0.95)
        context = generator._build_context(alert)
        
        # Test Business Intro
        script_biz = generator.templates["business_demo_info"].render(context)
        assert "ROI" in script_biz or "costly" in script_biz
        assert "uptime" in script_biz
        
        # Test Business Escalation
        script_esc = generator.templates["business_demo_critical"].render(context)
        assert "financial loss" in script_esc
        assert "High" in script_esc # business_impact

    def test_conclusion_script(self):
        """Verify conclusion script mentions all partners."""
        generator = VoiceScriptGenerator()
        alert = self._create_mock_alert("Conclusion", 0.0)
        context = generator._build_context(alert)
        
        script = generator.templates["demo_conclusion"].render(context)
        
        assert "Gemini" in script
        assert "Confluent" in script
        assert "Datadog" in script
        assert "ElevenLabs" in script
