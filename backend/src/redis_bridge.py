"""
Bridge between Redis Pub/Sub and local EventBus.
Enables inter-process event synchronization when Kafka is unavailable.
"""
import threading
import json
import logging
import time
from typing import Optional, Any

from .prediction_engine.redis_client import redis_client
from .event_bus import event_bus
from .logging_config import get_agent_logger

logger = logging.getLogger(__name__)
agent_logger = get_agent_logger(__name__)

class RedisEventBridge:
    """
    Synchronizes events between processes using Redis Pub/Sub.
    """
    
    def __init__(self, channel: str = "chorus_events"):
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.channel = channel
        self._pubsub = None
        self._is_bridging_local = False
        
    def start(self, bridge_local_events: bool = True):
        """
        Start the bridge.
        
        Args:
            bridge_local_events: If True, events published to the local event_bus 
                                will be sent to Redis.
        """
        if self.running:
            return
            
        self.running = True
        self._is_bridging_local = bridge_local_events
        
        # 1. Start listener thread
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        
        # 2. Subscribe local bus to broadcast to Redis
        if bridge_local_events:
            # We subscribe to all common event types
            event_types = [
                "trust_score_update", "conflict_prediction", "system_alert",
                "agent_quarantined", "intervention_executed", "voice_alert_generated",
                "agent_activity", "graph_update", "decision_update"
            ]
            for et in event_types:
                event_bus.subscribe(et, self._create_local_handler(et))
        
        logger.info(f"Redis Event Bridge started on channel: {self.channel}")
        
    def _create_local_handler(self, event_type: str):
        def handler(data):
            # Avoid infinite loops: check if this event came from the bridge itself
            if isinstance(data, dict) and data.get("_bridged"):
                return
                
            self.publish_to_redis(event_type, data)
        return handler

    def publish_to_redis(self, event_type: str, data: Any):
        """Broadcast a local event to other processes via Redis."""
        try:
            payload = {
                "type": event_type,
                "data": data,
                "_bridged": True,
                "sender_pid": time.time() # Simple unique id
            }
            redis_client._client.publish(self.channel, json.dumps(payload, default=str))
        except Exception as e:
            logger.error(f"Failed to publish to Redis: {e}")

    def stop(self):
        """Stop the bridge."""
        self.running = False
        if self._pubsub:
            try:
                self._pubsub.close()
            except:
                pass
        if self.thread:
            self.thread.join(timeout=2.0)
            
    def _listen_loop(self):
        """Main loop listening to Redis."""
        while self.running:
            try:
                self._pubsub = redis_client._client.pubsub()
                self._pubsub.subscribe(self.channel)
                logger.info(f"Subscribed to Redis channel: {self.channel}")
                
                for message in self._pubsub.listen():
                    if not self.running:
                        break
                    
                    if message['type'] == 'message':
                        try:
                            payload = json.loads(message['data'])
                            event_type = payload.get("type")
                            event_data = payload.get("data")
                            
                            if event_type and event_data:
                                # Mark as bridged to prevent local loopback
                                if isinstance(event_data, dict):
                                    event_data["_bridged"] = True
                                    
                                # Publish to local bus
                                event_bus.publish(event_type, event_data)
                        except Exception as e:
                            logger.error(f"Redis bridge decode error: {e}")
                            
            except Exception as e:
                logger.error(f"Redis bridge loop error: {e}")
                time.sleep(2.0)

# Global instance
redis_event_bridge = RedisEventBridge()
