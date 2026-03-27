"""
Stream processing pipeline for agent messages.
"""
import json
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

from .config import settings
from .logging_config import get_agent_logger
from .integrations.kafka_client import kafka_bus, KafkaOperationError
from .prediction_engine.intervention_engine import intervention_engine
from .prediction_engine.models.core import AgentIntention, ConflictAnalysis, ResourceType
from .prediction_engine.gemini_client import GeminiClient
from .prediction_engine.pattern_detector import pattern_detector
from .prediction_engine.redis_client import redis_client
from .stream_analytics import stream_analytics

agent_logger = get_agent_logger(__name__)

class StreamProcessor:
    """
    Processes stream of agent messages to predict and prevent conflicts.
    """
    
    def __init__(self):
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.input_topic = settings.kafka.agent_messages_topic
        self.output_topic = settings.kafka.agent_decisions_topic
        self.dlq_topic = "agent-messages-dlq" # Convention
        self.system_alerts_topic = settings.kafka.system_alerts_topic
        self.analytics_topic = settings.kafka.analytics_metrics_topic
        self.gemini_client = GeminiClient()
        self.history_ttl = 3600 # 1 hour history for pattern detection
        self.last_metrics_time = 0
        
    def start(self):
        """Start processing loop in a background thread."""
        if self.running:
            return
            
        self.running = True
        kafka_bus.subscribe([self.input_topic])
        
        self.thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.thread.start()
        
        agent_logger.log_agent_action(
            "INFO", 
            "Stream processor started", 
            action_type="stream_processor_start",
            context={"input_topic": self.input_topic}
        )

    def stop(self):
        """Stop processing loop."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)
            
        agent_logger.log_agent_action(
            "INFO", 
            "Stream processor stopped", 
            action_type="stream_processor_stop"
        )

    def _processing_loop(self):
        """Main processing loop."""
        while self.running:
            try:
                # Poll for messages
                msg = kafka_bus.poll(timeout=1.0)
                
                # Periodic metrics publication
                now = time.time()
                if now - self.last_metrics_time >= 1.0:
                    metrics = stream_analytics.get_aggregated_statistics()
                    kafka_bus.produce(
                        self.analytics_topic,
                        {"type": "stream_metrics", "data": metrics, "timestamp": now},
                        key="metrics"
                    )
                    self.last_metrics_time = now
                
                if msg is None:
                    continue
                    
                start_time = time.time()
                self._process_message(msg)
                
                # Record metrics
                processing_time_ms = (time.time() - start_time) * 1000
                stream_analytics.record_message()
                stream_analytics.record_latency(processing_time_ms)
                
                # Record metrics for stream monitoring
                try:
                    from .stream_monitoring import stream_monitor
                    stream_monitor.record_processing_latency(processing_time_ms)
                    stream_monitor.record_message_processed()
                except ImportError:
                    pass
                
                # Manual commit
                kafka_bus.commit()
                
            except Exception as e:
                stream_analytics.record_error()
                
                # Record error for stream monitoring
                try:
                    from .stream_monitoring import stream_monitor
                    stream_monitor.record_error()
                except ImportError:
                    pass
                
                agent_logger.log_system_error(e, "stream_processor", "loop")
                time.sleep(1.0) # Backoff on loop crash

    def _process_message(self, msg: Dict[str, Any]):
        """
        Process a single message.
        """
        try:
            payload = msg.get("value")
            if not payload:
                return

            # Parse AgentIntention
            try:
                intention = self._parse_intention(payload)
            except ValueError as e:
                agent_logger.log_agent_action(
                    "WARNING", 
                    f"Invalid message format: {e}",
                    action_type="invalid_message",
                    context={"payload": str(payload)[:200]}
                )
                return

            # Analyze and decide
            decision = self._analyze_intention(intention)
            
            # Produce decision
            kafka_bus.produce(
                self.output_topic,
                decision,
                key=msg.get("key")
            )
            
        except Exception as e:
            agent_logger.log_system_error(
                e, 
                "stream_processor", 
                "process_message", 
                context={"msg_offset": msg.get("offset")}
            )
            # Send to DLQ
            try:
                kafka_bus.produce(
                    self.dlq_topic,
                    {
                        "original_message": msg,
                        "error": str(e),
                        "timestamp": time.time()
                    },
                    key=msg.get("key")
                )
            except Exception as dlq_error:
                agent_logger.log_system_error(dlq_error, "stream_processor", "dlq_produce")

    def _parse_intention(self, payload: Dict[str, Any]) -> AgentIntention:
        """
        Parse raw payload into AgentIntention.
        """
        required_fields = ["agent_id", "resource_type", "requested_amount", "priority_level", "timestamp"]
        for field in required_fields:
            if field not in payload:
                raise ValueError(f"Missing required field: {field}")
                
        # Handle timestamp parsing
        ts_str = payload["timestamp"]
        if isinstance(ts_str, str):
            try:
                timestamp = datetime.fromisoformat(ts_str)
            except ValueError:
                # Try fallback format if needed, or raise
                timestamp = datetime.now() # Fallback? Or raise? Prefer raise for data integrity
                raise ValueError(f"Invalid timestamp format: {ts_str}")
        else:
            # Assume it's already a datetime or timestamp (if float/int)
            # But the requirement says "proper parsing", usually implies string from JSON
            raise ValueError(f"Invalid timestamp type: {type(ts_str)}")

        return AgentIntention(
            agent_id=payload["agent_id"],
            resource_type=payload["resource_type"],
            requested_amount=int(payload["requested_amount"]),
            priority_level=int(payload["priority_level"]),
            timestamp=timestamp
        )

    def _update_agent_history(self, intention: AgentIntention):
        """
        Update agent history in Redis for pattern detection.
        """
        try:
            key = f"agent_history:{intention.agent_id}"
            
            # Create a dict representation for storage
            entry = {
                "agent_id": intention.agent_id,
                "resource_type": intention.resource_type,
                "requested_amount": intention.requested_amount,
                "priority_level": intention.priority_level,
                "timestamp": intention.timestamp.isoformat()
            }
            
            # Use Redis list: LPUSH and LTRIM
            # We can't use simple set/get for a list easily with our RedisClient wrapper 
            # if it doesn't expose list operations directly.
            # Let's check RedisClient... it only has get/set/set_json.
            # But it has `_client` access or `_execute_with_retry`.
            
            # Accessing underlying client safely
            redis_client._execute_with_retry(redis_client._client.lpush, key, json.dumps(entry))
            redis_client._execute_with_retry(redis_client._client.ltrim, key, 0, 19) # Keep last 20
            redis_client._execute_with_retry(redis_client._client.expire, key, self.history_ttl)
            
        except Exception as e:
            agent_logger.log_system_error(e, "stream_processor", "update_history")

    def _get_agent_history(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve agent history from Redis.
        """
        try:
            key = f"agent_history:{agent_id}"
            raw_list = redis_client._execute_with_retry(redis_client._client.lrange, key, 0, -1)
            return [json.loads(item) for item in raw_list]
        except Exception as e:
            agent_logger.log_system_error(e, "stream_processor", "get_history")
            return []

    def _analyze_intention(self, intention: AgentIntention) -> Dict[str, Any]:
        """
        Analyze intention using Gemini and Pattern Detector.
        """
        # 0. Update Interaction Graph (for Loop Detection)
        if intention.resource_type.startswith("agent_attention:"):
            try:
                target_agent_id = intention.resource_type.split(":", 1)[1]
                pattern_detector.record_interaction(intention.agent_id, target_agent_id)
            except IndexError:
                pass

        # 1. Update and Get History for Pattern Detection
        self._update_agent_history(intention)
        history = self._get_agent_history(intention.agent_id)
        
        patterns = []
        pattern_details = {}
        
        # Detect routing loops
        loop = pattern_detector.detect_routing_loop(intention.agent_id)
        if loop and len(loop) >= 3:
            patterns.append("ROUTING_LOOP")
            affected = pattern_detector.get_affected_agents_in_loop(loop)
            pattern_details["ROUTING_LOOP"] = {
                "type": "routing_loop",
                "severity": "critical",
                "details": f"Circular dependency detected: {' -> '.join(loop)}. This can cause infinite message chains and system overload.",
                "recommended_action": "Break the loop by quarantining one of the agents in the cycle or implementing circuit breakers",
                "affected_agents": affected
            }
        
        # Detect resource hoarding
        if pattern_detector.detect_resource_hoarding(intention.agent_id, history):
            patterns.append("RESOURCE_HOARDING")
            pattern_details["RESOURCE_HOARDING"] = {
                "type": "resource_hoarding",
                "severity": "warning",
                "details": f"Agent {intention.agent_id} is consistently requesting high-priority resources without releasing them",
                "recommended_action": "Monitor resource allocation patterns and consider implementing resource quotas",
                "affected_agents": [intention.agent_id]
            }
        
        # Detect communication cascade
        if pattern_detector.detect_communication_cascade_by_agent(intention.agent_id):
            patterns.append("COMMUNICATION_CASCADE")
            pattern_details["COMMUNICATION_CASCADE"] = {
                "type": "communication_cascade",
                "severity": "warning",
                "details": f"Agent {intention.agent_id} is generating an abnormally high volume of messages, which may lead to system overload",
                "recommended_action": "Implement rate limiting or temporarily throttle this agent's message processing",
                "affected_agents": [intention.agent_id]
            }
        
        # Detect Byzantine behavior (if we have trust score history)
        try:
            from .prediction_engine.trust_manager import trust_manager
            trust_history = trust_manager.get_agent_history(intention.agent_id)
            if pattern_detector.detect_byzantine_behavior(intention.agent_id, trust_history):
                patterns.append("BYZANTINE_BEHAVIOR")
                pattern_details["BYZANTINE_BEHAVIOR"] = {
                    "type": "byzantine_behavior",
                    "severity": "critical",
                    "details": f"Agent {intention.agent_id} is exhibiting inconsistent behavior patterns that may indicate malicious activity",
                    "recommended_action": "Quarantine agent immediately and investigate communication patterns",
                    "affected_agents": [intention.agent_id]
                }
        except Exception as e:
            agent_logger.log_system_error(e, "stream_processor", "byzantine_detection")
        
        # 2. Gemini Analysis
        try:
            # We pass a list of intentions. 
            # Ideally we'd include other concurrent intentions, but for now just this one.
            analysis = self.gemini_client.analyze_conflict_risk([intention])
        except Exception as e:
            # If Gemini fails, we should still proceed with a fallback or error decision
            agent_logger.log_system_error(e, "stream_processor", "gemini_analysis")
            # Create a fallback analysis
            analysis = ConflictAnalysis(
                risk_score=0.5, # Moderate risk on error
                confidence_level=0.0,
                affected_agents=[intention.agent_id],
                predicted_failure_mode="Analysis unavailable",
                nash_equilibrium=None,
                timestamp=datetime.now()
            )

        # 3. Integrate Pattern Detection
        if patterns:
            analysis.predicted_failure_mode = f"{analysis.predicted_failure_mode} | Patterns: {', '.join(patterns)}"
            # Elevate risk if patterns detected
            if analysis.risk_score < 0.9:
                analysis.risk_score = min(analysis.risk_score + 0.3, 1.0)
                
        # 4. Intervention Engine
        intervention_result = intervention_engine.process_conflict_analysis(analysis)
        
        status = "QUARANTINED" if intervention_result else "APPROVED"
        
        return {
            "decision_id": f"dec_{int(time.time())}_{intention.agent_id}",
            "agent_id": intention.agent_id,
            "resource_type": intention.resource_type,
            "requested_amount": intention.requested_amount,
            "status": status,
            "risk_score": analysis.risk_score,
            "patterns_detected": patterns,
            "pattern_details": pattern_details,
            "processed_at": time.time(),
            "intervention_result": intervention_result.reason if intervention_result else None
        }

# Global instance
stream_processor = StreamProcessor()