"""
Demo scenario orchestration engine.
"""
import logging
import time
import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

from .models.alert import ClassifiedAlert, AlertSeverity, AlertContext, ImpactAssessment
from .alert_delivery_engine import alert_delivery_engine
from .voice_script_generator import script_generator
from ..integrations.elevenlabs_client import voice_client

logger = logging.getLogger(__name__)

@dataclass
class DemoStep:
    action: str
    delay: float
    narration: Optional[str] = None
    template_key: Optional[str] = None # Key for dynamic script generation
    alert: Optional[ClassifiedAlert] = None

class DemoScenarioEngine:
    """
    Orchestrates predefined demo scenarios with voice narration.
    """
    
    def __init__(self):
        self.running = False
        self.audience = "technical" # Default audience
        self.scenarios: Dict[str, List[DemoStep]] = {}
        self._initialize_scenarios()
        
    def _initialize_scenarios(self):
        """Define standard demo scenarios."""
        
        # Scenario 1: Routing Loop (Dynamic)
        self.scenarios["routing_loop"] = [
            DemoStep(
                action="init",
                delay=0,
                template_key="demo_info" # technical_demo_info or business_demo_info
            ),
            DemoStep(
                action="loop_start",
                delay=2.0,
                alert=self._create_alert(
                    "WARNING: Circular dependency detected", 
                    AlertSeverity.WARNING,
                    "Agents A -> B -> C -> A pattern identified."
                )
            ),
            DemoStep(
                action="escalation",
                delay=4.0,
                template_key="demo_critical"
            ),
            DemoStep(
                action="intervention",
                delay=3.0,
                alert=self._create_alert(
                    "CRITICAL: Routing Loop Amplification",
                    AlertSeverity.CRITICAL,
                    "Traffic spike detected in circular path. Initiating quarantine for Agent A."
                )
            ),
            DemoStep(
                action="resolution",
                delay=5.0,
                template_key="demo_conclusion"
            )
        ]

        # Scenario 2: Resource Hoarding (Legacy/Static for comparison if needed, or update)
        self.scenarios["resource_hoarding"] = [
            DemoStep(
                action="init",
                delay=0,
                narration="Starting resource hoarding simulation. Agent X is requesting excessive CPU."
            ),
            # ... existing steps ...
            DemoStep(
                action="detect",
                delay=3.0,
                alert=self._create_alert(
                    "WARNING: Resource usage anomaly",
                    AlertSeverity.WARNING,
                    "Agent X exceeding baseline CPU usage by 400%."
                )
            ),
            DemoStep(
                action="quarantine",
                delay=4.0,
                alert=self._create_alert(
                    "EMERGENCY: Service Degradation",
                    AlertSeverity.EMERGENCY,
                    "Critical resource exhaustion. Quarantining Agent X immediately."
                )
            )
        ]

    def set_audience(self, audience: str):
        """Set target audience for narration."""
        self.audience = audience

    def _create_alert(self, title: str, severity: AlertSeverity, desc: str) -> ClassifiedAlert:
        """Helper to create mock alerts."""
        from datetime import datetime
        return ClassifiedAlert(
            severity=severity,
            title=title,
            description=desc,
            impact=ImpactAssessment(0.8, 0.8, 10, [], "Demo impact"),
            recommended_action="Demo action",
            requires_voice_alert=True,
            context=AlertContext("demo", ["demo_agent"], timestamp=datetime.now()),
            timestamp=datetime.now()
        )

    def run_scenario(self, name: str):
        """Execute a scenario in a background thread."""
        if name not in self.scenarios:
            logger.error(f"Scenario {name} not found")
            return
            
        if self.running:
            logger.warning("A scenario is already running")
            return

        self.running = True
        threading.Thread(target=self._execute_steps, args=(self.scenarios[name],), daemon=True).start()
        logger.info(f"Started scenario: {name}")

    def _execute_steps(self, steps: List[DemoStep]):
        """Execute steps sequentially."""
        try:
            for step in steps:
                if not self.running:
                    break
                
                # 1. Narration
                text_to_speak = step.narration
                
                if step.template_key:
                    # Resolve template based on audience
                    # Logic: Try {audience}_{key}, then {key}, then fail
                    key_with_audience = f"{self.audience}_{step.template_key}"
                    template = script_generator.templates.get(key_with_audience) or script_generator.templates.get(step.template_key)
                    
                    if template:
                        # Create a mock context for the demo
                        # In a real system this might come from live state
                        ctx = {
                            "agent_count": "3",
                            "risk_score": "0.95",
                            "business_impact": "High"
                        }
                        text_to_speak = template.render(ctx)
                
                if text_to_speak and voice_client.enabled:
                    voice_client.generate_alert(text_to_speak)
                
                # 2. Alert Injection
                if step.alert:
                    alert_delivery_engine.process_alert(step.alert)
                
                # 3. Wait
                time.sleep(step.delay)
                
        except Exception as e:
            logger.error(f"Scenario execution failed: {e}")
        finally:
            self.running = False
            logger.info("Scenario finished")

    def stop_scenario(self):
        """Stop current scenario."""
        self.running = False

# Global instance
demo_engine = DemoScenarioEngine()
