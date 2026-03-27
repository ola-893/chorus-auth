"""
Voice script generation engine for contextual alerts.
"""
import logging
from typing import Dict, Optional
from string import Template

from .models.alert import ClassifiedAlert, AlertSeverity, AlertContext

logger = logging.getLogger(__name__)

class ScriptTemplate:
    """Template for voice scripts."""
    def __init__(self, name: str, text: str, description: str):
        self.name = name
        self.template = Template(text)
        self.description = description

    def render(self, context: Dict[str, str]) -> str:
        return self.template.safe_substitute(context)

class VoiceScriptGenerator:
    """
    Generates contextual voice scripts based on alert classification.
    """
    
    def __init__(self):
        self.templates: Dict[str, ScriptTemplate] = {}
        self._initialize_default_templates()
        
    def _initialize_default_templates(self):
        """Initialize default script templates."""
        
        # Technical Audience Templates
        self.templates["technical_critical"] = ScriptTemplate(
            "technical_critical",
            "Critical alert. High-risk conflict detected involving ${agent_count} agents. "
            "Predicted failure mode: ${failure_mode}. "
            "Risk score is ${risk_score}. Immediate intervention required.",
            "Technical detail for critical incidents"
        )
        
        self.templates["technical_warning"] = ScriptTemplate(
            "technical_warning",
            "Warning. Potential conflict pattern identified. "
            "Trust trend for ${agent_count} agents is degrading. Monitor system metrics.",
            "Technical detail for warnings"
        )
        
        # Business Audience Templates
        self.templates["business_critical"] = ScriptTemplate(
            "business_critical",
            "Urgent notification. System stability is at risk. "
            "Estimated business impact is ${business_impact}. "
            "Automated quarantine protocols have been activated.",
            "High-level impact summary"
        )
        
        # Default Fallback
        self.templates["default"] = ScriptTemplate(
            "default",
            "Alert received. Severity: ${severity}. ${description}",
            "Generic fallback template"
        )

        # ---------------------------------------------------------
        # Demo Narration Templates (Task 8)
        # ---------------------------------------------------------

        # Technical: Deep dive into Game Theory & Nash Equilibrium
        self.templates["technical_demo_info"] = ScriptTemplate(
            "technical_demo_info",
            "Initiating technical demonstration. Observing ${agent_count} autonomous agents. "
            "Gemini 3 Pro is analyzing strategic interactions in real-time. "
            "Searching for Nash Equilibria where unilateral deviation provides no benefit. "
            "Current system state is stable, but high-frequency resource requests suggest emerging contention.",
            "Technical intro focusing on game theory"
        )

        self.templates["technical_demo_critical"] = ScriptTemplate(
            "technical_demo_critical",
            "Escalation detected. Agents have deviated from the cooperative equilibrium. "
            "Calculated Shapley values indicate Agent A is contributing disproportionately to the instability. "
            "Risk score has spiked to ${risk_score}. "
            "The system is approaching a cascading failure horizon.",
            "Technical escalation with game theory concepts"
        )

        # Business: Focus on Cost & Impact
        self.templates["business_demo_info"] = ScriptTemplate(
            "business_demo_info",
            "Welcome to the Chorus operational dashboard. "
            "We are monitoring a live fleet of ${agent_count} service agents. "
            "This automated safety layer protects your infrastructure from costly cascading failures, "
            "ensuring 99.99% uptime and preventing resource waste.",
            "Business intro focusing on ROI"
        )

        self.templates["business_demo_critical"] = ScriptTemplate(
            "business_demo_critical",
            "Critical risk identified. A resource loop is threatening service availability. "
            "Projected impact: ${business_impact} financial loss per minute. "
            "Automated intervention protocols are engaging to prevent service outage.",
            "Business escalation focusing on financial impact"
        )

        # Conclusion: All Partners Showcase
        self.templates["demo_conclusion"] = ScriptTemplate(
            "demo_conclusion",
            "Demonstration complete. "
            "You have just seen Chorus predict and prevent a failure in real-time. "
            "Powered by Google Gemini's reasoning, Confluent's data streaming, "
            "Datadog's observability, and ElevenLabs' voice interface. "
            "System is now stable. Trust scores are recovering.",
            "Comprehensive partner showcase conclusion"
        )

    def generate_script(self, alert: ClassifiedAlert, audience: str = "technical") -> str:
        """
        Generate a voice script for a classified alert.
        
        Args:
            alert: The classified alert object.
            audience: Target audience ('technical' or 'business').
            
        Returns:
            Generated script text.
        """
        template_key = self._select_template(alert, audience)
        template = self.templates.get(template_key, self.templates["default"])
        
        context = self._build_context(alert)
        return template.render(context)

    def _select_template(self, alert: ClassifiedAlert, audience: str) -> str:
        """Select appropriate template based on alert and audience."""
        if alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY]:
            severity_key = "critical"
        elif alert.severity == AlertSeverity.WARNING:
            severity_key = "warning"
        else:
            # INFO or others fallback to default immediately or try "info"
            severity_key = "info"
            
        key = f"{audience}_{severity_key}"
        
        if key in self.templates:
            return key
        return "default"

    def _build_context(self, alert: ClassifiedAlert) -> Dict[str, str]:
        """Build substitution context from alert."""
        return {
            "severity": alert.severity.value,
            "agent_count": str(len(alert.context.affected_agents)),
            "failure_mode": alert.title.split(": ")[1] if ": " in alert.title else "Unknown",
            "risk_score": f"{alert.context.risk_score:.2f}",
            "business_impact": "High" if alert.impact.business_impact_score > 0.7 else "Moderate",
            "description": alert.description,
            "recommended_action": alert.recommended_action
        }

    def add_template(self, name: str, text: str, description: str):
        """Add or update a custom template."""
        self.templates[name] = ScriptTemplate(name, text, description)

# Global instance
script_generator = VoiceScriptGenerator()
