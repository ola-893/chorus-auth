"""
Bridge between Kafka topics and local EventBus.
Enables API streaming updates from distributed components.
"""
import threading
import json
import logging
import time
from typing import Optional

from .integrations.kafka_client import kafka_bus
from .event_bus import event_bus
from .config import settings
from .logging_config import get_agent_logger

logger = logging.getLogger(__name__)
agent_logger = get_agent_logger(__name__)

class KafkaEventBridge:
    """
    Consumes Kafka messages and republishes them to the local EventBus.
    """
    
    def __init__(self):
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.topics = [
            settings.kafka.agent_messages_topic,
            settings.kafka.agent_decisions_topic,
            settings.kafka.system_alerts_topic,
            settings.kafka.causal_graph_updates_topic,
            settings.kafka.analytics_metrics_topic
        ]
        
    def start(self):
        """Start the bridge in a background thread."""
        if self.running or not kafka_bus.enabled:
            return
            
        self.running = True
        kafka_bus.subscribe(self.topics)
        
        self.thread = threading.Thread(target=self._consumption_loop, daemon=True)
        self.thread.start()
        logger.info(f"Kafka Event Bridge started, listening to {self.topics}")
        
    def stop(self):
        """Stop the bridge."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
            
    def _consumption_loop(self):
        """Main loop."""
        while self.running:
            try:
                # Create a temporary consumer for the bridge
                group_id = f"chorus-api-bridge-{int(time.time())}"
                logger.info(f"Bridge creating consumer with group ID: {group_id}")
                consumer = kafka_bus.create_temporary_consumer(group_id=group_id)
                if not consumer:
                    logger.error("Bridge failed to create consumer")
                    time.sleep(5)
                    continue
                    
                logger.info(f"Bridge subscribing to topics: {self.topics}")
                consumer.subscribe(self.topics)
                
                while self.running:
                    msg = consumer.poll(1.0)
                    if msg is None:
                        # Log periodically to show it's still polling
                        if int(time.time()) % 10 == 0:
                            logger.info(f"Bridge polling {self.topics}... (no messages)")
                        continue
                    if msg.error():
                        logger.error(f"Kafka consumer error: {msg.error()}")
                        continue
                        
                    try:
                        logger.info(f"Bridge received message on {msg.topic()}: {msg.value().decode('utf-8')[:100]}...")
                        val = json.loads(msg.value().decode('utf-8'))
                        topic = msg.topic()
                        
                        # Dynamic dispatch based on payload type
                        msg_type = val.get("type") or val.get("action_type")
                        if msg_type:
                            # Standardize on certain types for the frontend
                            if msg_type == "resource_request":
                                event_bus.publish("agent_activity", val)
                            else:
                                event_bus.publish(msg_type, val)
                        
                        # Fallback based on topic if no type found
                        if topic == settings.kafka.agent_messages_topic:
                            event_bus.publish("agent_activity", val)
                        elif topic == settings.kafka.agent_decisions_topic:
                            # Decision topic usually contains richer metadata or patterns
                            event_bus.publish("decision_update", val)
                        elif topic == settings.kafka.system_alerts_topic:
                            event_bus.publish("system_alert", val)
                        elif topic == settings.kafka.causal_graph_updates_topic:
                            logger.info("Bridge received graph update")
                            event_bus.publish("graph_update", val)
                        elif topic == settings.kafka.analytics_metrics_topic:
                            event_bus.publish("system_alert", val)
                            
                    except Exception as e:
                        logger.error(f"Bridge decode error: {e}")
                        
            except Exception as e:
                logger.error(f"Bridge loop error: {e}")
                time.sleep(2.0)

# Global instance
kafka_event_bridge = KafkaEventBridge()
