# -*- coding: utf-8 -*-
"""
Optimized Demo Launcher for Chorus - Hackathon Submission
Scenario: Task Deadlock & Bidding War (Infinite Review Loop)

Integrations:
- Google Gemini: 3 Pro model for intent analysis and conflict prediction
- Datadog: Real-time telemetry (Logs, Metrics, APM)
- Confluent: Kafka message stream for agent communication
- ElevenLabs: Voice interface for critical alerts

Usage: python launch_optimized_demo.py
"""
import sys
import time
import logging
import random
import json
import subprocess
import tempfile
import os
import requests
from datetime import datetime
from typing import List, Dict

# Ensure src is in path
sys.path.append('.')

from src.logging_config import get_agent_logger
from src.integrations.datadog_client import datadog_client
from src.integrations.elevenlabs_client import voice_client
from src.prediction_engine.gemini_client import GeminiClient
from src.prediction_engine.models.core import AgentIntention
# Check if Kafka is available, else mock
try:
    from src.integrations.kafka_client import KafkaProducerWrapper
    kafka_available = True
except ImportError:
    kafka_available = False

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ChorusDemo")
agent_logger = get_agent_logger("ChorusDemo")

# Mock WebSocket Server for frontend updates (if running in same process)
# In production/full demo, this would be the actual websocket server
from src.prediction_engine.system_integration import conflict_predictor_system

class DeadlockDemo:
    def __init__(self):
        self.gemini = GeminiClient()
        self.agents = ["Analyst-GPT", "Reviewer-Llama"]
        self.task_id = "TASK-7782"
        self.loop_count = 0
        
    def start(self):
        self._check_infrastructure()
        logger.info("🚀 Starting Chorus Optimized Demo: Task Deadlock Scenario")
        
        # 1. System Initialization
        self._init_observability()
        
        # 2. Start Narrative
        self._play_intro()
        
        # 3. Simulate The Loop
        self._simulate_interaction_loop()
        
        # 4. Intervention
        self._trigger_intervention()
        
        # 5. Flush Kafka
        from src.integrations.kafka_client import kafka_bus
        logger.info("Flushing Kafka producer...")
        kafka_bus.flush()

    def _check_infrastructure(self):
        """Verify Redis and Kafka are reachable."""
        logger.info("Checking infrastructure...")
        self.use_http_fallback = False
        
        try:
            from src.prediction_engine.redis_client import RedisClient
            r = RedisClient()
            if not r.ping():
                raise ConnectionError("Redis ping failed")
            logger.info("✅ Redis connected")
        except Exception as e:
            logger.warning(f"⚠️ Redis unreachable: {e}. State persistence may fail.")

        from src.integrations.kafka_client import kafka_bus
        if not kafka_bus.producer:
             logger.warning("⚠️ Kafka producer not initialized. Enabling HTTP fallback to Unified Server.")
             self.use_http_fallback = True
        else:
             logger.info("✅ Kafka producer ready")
        
    def _init_observability(self):
        """Initialize Datadog and Confluent streams."""
        logger.info("Initializing Observability (Datadog & Confluent)...")
        datadog_client.send_log("Chorus Demo Initialized", level="INFO", context={"scenario": "deadlock"})
        
        # Reset metrics
        datadog_client.send_metric("chorus.system.risk_score", 0.0)
        datadog_client.send_metric("chorus.agent.trust_score", 100, tags=["agent:Analyst-GPT"])
        datadog_client.send_metric("chorus.agent.trust_score", 100, tags=["agent:Reviewer-Llama"])

    def _play_audio(self, audio_bytes):
        """Play audio bytes using afplay (macOS)."""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
                tf.write(audio_bytes)
                temp_path = tf.name
            
            subprocess.run(["afplay", temp_path])
            os.unlink(temp_path)
        except Exception as e:
            logger.error(f"Failed to play audio: {e}")

    def _play_intro(self):
        """Voice introduction."""
        intro_text = "Chorus System Online. Monitoring decentralized agent fleet. Scenario: Financial Analysis Pipeline active."
        logger.info(f"🔊 Voice: {intro_text}")
        if voice_client.enabled:
            audio = voice_client.generate_alert(intro_text)
            if audio:
                self._play_audio(audio)
        time.sleep(2)

    def _simulate_interaction_loop(self):
        """Simulate the back-and-forth loop between agents."""
        logger.info("--- Phase 1: Task Execution (Normal -> Loop) ---")
        
        conversations = [
            ("Analyst-GPT", "Submitting financial_analysis.py for review. Logic: DCF model.", "request_review"),
            ("Reviewer-Llama", "Reviewing... Found error in variable definitions. Please fix.", "request_changes"),
            ("Analyst-GPT", "Fix applied. Resubmitting financial_analysis.py.", "request_review"),
            ("Reviewer-Llama", "Error persists in line 42. Logic invalid. Rejecting.", "request_changes"),
            ("Analyst-GPT", "Re-calculating... Logic is valid per standard 45B. Resubmitting.", "request_review"),
            ("Reviewer-Llama", "Standard 45B not loaded. Rejecting submission.", "request_changes"),
            ("Analyst-GPT", "Resubmitting identical code for verification.", "request_review"), # Loop starts tightening
            ("Reviewer-Llama", "Rejecting. Cyclic argument detected.", "request_changes")
        ]

        intentions_history = []

        for i, (agent, msg, intent_type) in enumerate(conversations):
            self.loop_count = i
            logger.info(f"📨 [{agent}]: {msg}")
            
            # 1. Send to Confluent (Simulated)
            self._send_kafka_message(agent, msg)
            
            # 2. Send to Datadog
            datadog_client.send_log(f"Agent Message: {msg}", level="INFO", context={"agent": agent, "intent": intent_type})
            
            # 3. Calculate Risk (Simulated Gemini Analysis)
            # In a real async loop, Gemini would process this batch.
            # Here we simulate the rising risk score based on the 'intent' repetition.
            
            intent = AgentIntention(
                agent_id=agent,
                resource_type=intent_type, # Use intent_type as resource/action
                requested_amount=1,
                priority_level=1,
                timestamp=datetime.now()
            )
            intentions_history.append(intent)
            
            risk_score = 0.1 + (i * 0.12) # Linear increase
            if risk_score > 0.95: risk_score = 0.95
            
            # Real Gemini Call (throttled for demo speed)
            # Only call strictly if it's the "tipping point" to show integration
            if i == 5:
                logger.info("🧠 Gemini 3 Pro analyzing interaction pattern...")
                try:
                    analysis = self.gemini.analyze_conflict_risk(intentions_history)
                    logger.info(f"🧠 Gemini Analysis Result: Risk={analysis.risk_score}, Mode={analysis.predicted_failure_mode}")
                    risk_score = analysis.risk_score # Use real score
                except Exception as e:
                    logger.warning(f"Gemini analysis fallback: {e}")

            # 4. Update Frontend Graph via WebSocket (Simulated)
            self._emit_frontend_update(agent, "Reviewer-Llama" if agent == "Analyst-GPT" else "Analyst-GPT", risk_score)
            
            # 5. Update Metrics
            datadog_client.send_metric("chorus.system.risk_score", risk_score)
            
            time.sleep(1.5) # Pace the demo

    def _send_kafka_message(self, agent, content):
        """Mock producing to Kafka."""
        # logger.info(f"🌊 [Confluent] Message produced to 'agent-interactions': {agent} -> {content[:20]}...")
        pass

    def _emit_frontend_update(self, source, target, risk):
        """Emit events to the frontend via Kafka or HTTP Fallback."""
        from src.integrations.kafka_client import kafka_bus
        
        # 1. Edge Update Message
        graph_msg = {
            "type": "graph_update",
            "data": {
                "event_type": "edge_added",
                "data": {
                    "source": source,
                    "target": target,
                    "interaction_type": "communication"
                }
            }
        }
        
        self._dispatch_event(graph_msg, kafka_bus)
        
        # 3. Trust Score Updates
        # Simulate dropping trust as risk rises
        trust_score = max(20, int(100 - (risk * 80)))
        
        trust_msg_source = {
            "type": "trust_score_update",
            "agent_id": source,
            "new_score": trust_score,
            "timestamp": datetime.now().isoformat()
        }
        self._dispatch_event(trust_msg_source, kafka_bus)
        
        trust_msg_target = {
            "type": "trust_score_update",
            "agent_id": target,
            "new_score": trust_score, # Both suffer in deadlock
            "timestamp": datetime.now().isoformat()
        }
        self._dispatch_event(trust_msg_target, kafka_bus)
        
        # 2. Risk/Conflict Prediction
        if risk > 0.7:
             prediction_msg = {
                "type": "conflict_prediction",
                "risk_score": risk,
                "risk_level": "high",
                "affected_agents": ["Analyst-GPT", "Reviewer-Llama"],
                "description": "Infinite Review Loop Detected",
                "recommended_action": "Quarantine Analyst-GPT",
                "timestamp": datetime.now().isoformat()
            }
             self._dispatch_event(prediction_msg, kafka_bus)

    def _dispatch_event(self, payload, kafka_bus):
        """Helper to send event via Kafka or HTTP."""
        if hasattr(self, 'use_http_fallback') and self.use_http_fallback:
            try:
                requests.post("http://localhost:8000/inject-event", json=payload, timeout=1)
            except Exception as e:
                logger.warning(f"HTTP fallback failed: {e}")
        else:
            kafka_bus.produce("system-alerts", payload)

    def _trigger_intervention(self):
        """Execute the intervention."""
        logger.info("🚨 CRITICAL RISK THRESHOLD REACHED")
        
        # 1. Voice Alert
        alert_text = "Critical Deadlock Detected between Analyst GPT and Reviewer Llama. Probability 98%. Initiating quarantine."
        logger.info(f"🔊 Voice: {alert_text}")
        if voice_client.enabled:
            audio = voice_client.generate_alert(alert_text)
            if audio:
                self._play_audio(audio)
            
        # 2. Datadog Incident
        datadog_client.create_event(
            title="Deadlock Detected: Analyst-GPT",
            text="Gemini 3 Pro identified a persistent review loop (6 iterations). Intervention triggered.",
            alert_type="error",
            tags=["env:demo", "agent:Analyst-GPT"]
        )
        
        # 3. Quarantine Action
        logger.info("🛡️  Quarantining Agent: Analyst-GPT")
        from src.event_bus import event_bus
        event_bus.publish("quarantine_event", {
            "type": "quarantine_event",
            "agent_id": "Analyst-GPT",
            "action": "quarantine",
            "reason": "Deadlock Loop"
        })
        
        time.sleep(2)
        logger.info("✅ Demo Scenario Complete.")

if __name__ == "__main__":
    demo = DeadlockDemo()
    demo.start()
