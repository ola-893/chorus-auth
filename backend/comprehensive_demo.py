"""
Comprehensive Demo Orchestrator for Chorus.

This script runs end-to-end demo scenarios showcasing all partner technologies:
1. Google Gemini: Conflict prediction and game theory analysis
2. Datadog: Real-time monitoring and alerting
3. Confluent: Event streaming and message bus
4. ElevenLabs: Voice-first incident reporting
"""
import time
import logging
import random
from typing import Optional
from datetime import datetime

from src.prediction_engine.system_integration import conflict_predictor_system
from src.prediction_engine.demo_scenario_engine import demo_engine
from src.prediction_engine.voice_script_generator import script_generator
from src.prediction_engine.alert_delivery_engine import alert_delivery_engine
from src.prediction_engine.models.core import AgentIntention
from src.integrations.datadog_client import datadog_client
from src.integrations.elevenlabs_client import voice_client
from src.logging_config import get_agent_logger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
agent_logger = get_agent_logger(__name__)

class ComprehensiveDemo:
    def __init__(self):
        self.system = conflict_predictor_system
        self.scenario_engine = demo_engine
        
    def start(self, audience: str = "technical"):
        """Start the comprehensive demo."""
        logger.info(f"Starting Chorus Comprehensive Demo (Audience: {audience})")
        
        # 1. Initialize System
        self.system.start_system(agent_count=6)
        self.scenario_engine.set_audience(audience)
        
        # 2. Datadog: Send initialization event
        datadog_client.send_log(
            "Chorus Demo Started", 
            level="INFO", 
            context={"audience": audience, "timestamp": datetime.now().isoformat()}
        )
        
        try:
            # 3. Scenario 1: Stable State
            self._run_stable_state()
            
            # 4. Scenario 2: Routing Loop (Gemini + ElevenLabs + Confluent)
            self._run_routing_loop_scenario()
            
            # 5. Scenario 3: Conclusion
            self._run_conclusion()
            
        except KeyboardInterrupt:
            logger.info("Demo interrupted by user")
        finally:
            self.stop()

    def _run_stable_state(self):
        """Simulate stable system operation."""
        logger.info("--- Phase 1: Stable Operation ---")
        
        # Voice Intro
        intro_key = f"{self.scenario_engine.audience}_demo_info"
        template = script_generator.templates.get(intro_key)
        if template:
            intro_text = template.render({
                "agent_count": "6",
                "risk_score": "0.12",
                "business_impact": "None"
            })
            voice_client.generate_alert(intro_text)
        
        # Simulate traffic
        for _ in range(10): # Reduced from 15 to 10
            time.sleep(3) # Increased from 2 to 3
            # Log healthy metrics to Datadog
            datadog_client.send_metric("chorus.system.risk_score", random.uniform(0.1, 0.2))

    def _run_routing_loop_scenario(self):
        """Execute the routing loop failure scenario."""
        logger.info("--- Phase 2: Emerging Conflict (Routing Loop) ---")
        
        # Trigger the scenario engine
        # This handles the voice narration and alert injection sequence
        self.scenario_engine.run_scenario("routing_loop")
        
        # While scenario runs, simulate the backend metrics
        # simulating Gemini analysis of the loop
        for i in range(15): # Reduced from 20 to 15
            risk = 0.3 + (i * 0.05) # Escalating risk
            if risk > 1.0: risk = 0.99
            
            datadog_client.send_metric("chorus.system.risk_score", risk)
            
            if i == 8: # Threshold reached near middle
                # Critical threshold crossed
                logger.warning("Risk threshold exceeded! Triggering intervention.")
            
            time.sleep(3) # Increased from 2 to 3

    def _run_conclusion(self):
        """Wrap up the demo."""
        logger.info("--- Phase 3: Conclusion ---")
        # The scenario engine's "routing_loop" includes a conclusion step, 
        # but we can add a final system shutdown narration here if needed.
        
        final_text = script_generator.templates["demo_conclusion"].render({})
        # voice_client.generate_alert(final_text) # Engine handles this

    def stop(self):
        """Stop all systems."""
        logger.info("Stopping demo system...")
        self.system.stop_system()
        datadog_client.send_log("Chorus Demo Finished", level="INFO")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--audience", default="technical", choices=["technical", "business"])
    args = parser.parse_args()
    
    demo = ComprehensiveDemo()
    demo.start(audience=args.audience)
