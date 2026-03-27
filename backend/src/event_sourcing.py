"""
Event sourcing module for historical data access and replay.
"""
import json
import time
import logging
from typing import Dict, Any, List, Optional, Callable, Generator
from datetime import datetime

from .config import settings
from .logging_config import get_agent_logger
from .integrations.kafka_client import kafka_bus

try:
    from confluent_kafka import TopicPartition, KafkaError
except ImportError:
    TopicPartition = None
    KafkaError = None

agent_logger = get_agent_logger(__name__)
logger = logging.getLogger(__name__)

class EventLogManager:
    """
    Manages event sourcing, replay, and historical queries.
    """
    
    def __init__(self):
        self.kafka_bus = kafka_bus
        self.msg_topic = settings.kafka.agent_messages_topic
        self.decision_topic = settings.kafka.agent_decisions_topic
        self._buffer = []
        self._max_buffer = 1000
        
    def _record_event(self, topic: str, value: Any, key: Optional[str] = None):
        """Record an event in the local buffer for demo purposes."""
        event = {
            "topic": topic,
            "value": value,
            "key": key,
            "timestamp": int(time.time() * 1000),
            "offset": len(self._buffer)
        }
        self._buffer.append(event)
        if len(self._buffer) > self._max_buffer:
            self._buffer.pop(0)

    def replay_events(
        self, 
        topic: str, 
        start_time: Optional[datetime] = None, 
        end_time: Optional[datetime] = None,
        filter_func: Optional[Callable[[Dict[str, Any]], bool]] = None,
        limit: int = 1000
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Replay events from a topic within a time range.
        
        Args:
            topic: Topic name
            start_time: Start time (optional)
            end_time: End time (optional)
            filter_func: Filter function (optional)
            limit: Maximum number of events to yield
        
        Yields:
            Event dictionary
        """
        # Always check local buffer first - this is vital for the demo as it contains
        # the most recent events captured by the bridge
        buffer_events = []
        count = 0
        for event in self._buffer:
            if event["topic"] != topic:
                continue
            
            ts = event["timestamp"]
            if start_time and ts < int(start_time.timestamp() * 1000):
                continue
            if end_time and ts > int(end_time.timestamp() * 1000):
                continue
            
            val = event["value"]
            if filter_func and not filter_func(val):
                continue
                
            buffer_events.append({
                "value": val,
                "key": event["key"],
                "timestamp": ts,
                "offset": event["offset"],
                "source": "buffer"
            })
            count += 1
            if count >= limit:
                break
        
        # Yield buffer events
        for e in buffer_events:
            yield e
            
        if count >= limit or not self.kafka_bus.enabled:
            return

        # If we still have room, try to fetch from Kafka
        remaining_limit = limit - count
        consumer = self.kafka_bus.create_temporary_consumer()
        if not consumer:
            logger.error("Failed to create consumer for replay")
            return
            
        try:
            # seek to start time
            if start_time:
                ts_ms = int(start_time.timestamp() * 1000)
                offsets = self.kafka_bus.get_topic_offsets_for_time(consumer, topic, ts_ms)
                if offsets:
                    consumer.assign(offsets)
                else:
                    consumer.subscribe([topic])
            else:
                consumer.subscribe([topic])
                
            kafka_count = 0
            end_ts_ms = int(end_time.timestamp() * 1000) if end_time else None
            
            # To avoid duplicates if the buffer already has some Kafka messages
            buffer_offsets = {e["offset"] for e in buffer_events if e.get("source") != "buffer"} # Buffer events have local offsets though
            # Actually, local offsets in buffer are just indices. Kafka offsets are different.
            # For now, we'll just yield them and let the frontend handle deduplication or just show all.
            
            while kafka_count < remaining_limit:
                msg = consumer.poll(1.0)
                if msg is None:
                    break
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f"Replay error: {msg.error()}")
                        break
                        
                # Check end time
                if end_ts_ms and msg.timestamp()[1] > end_ts_ms:
                    break
                    
                # Deserialize
                try:
                    val = json.loads(msg.value().decode('utf-8'))
                except:
                    continue
                    
                # Filter
                if filter_func and not filter_func(val):
                    continue
                    
                yield {
                    "value": val,
                    "key": msg.key().decode('utf-8') if msg.key() else None,
                    "timestamp": msg.timestamp()[1],
                    "offset": msg.offset(),
                    "source": "kafka"
                }
                kafka_count += 1
                
        finally:
            consumer.close()

    def get_agent_history(
        self, 
        agent_id: str, 
        start_time: Optional[datetime] = None, 
        end_time: Optional[datetime] = None,
        event_type: str = "all"
    ) -> List[Dict[str, Any]]:
        """
        Get historical events for a specific agent.
        
        Args:
            agent_id: Agent ID
            start_time: Start time
            end_time: End time
            event_type: "message", "decision", or "all"
        
        Returns:
            List of events
        """
        events = []
        
        def agent_filter(payload):
            # Check for agent_id in common places
            aid = payload.get("agent_id") or payload.get("sender_id")
            return aid == agent_id

        if event_type in ["message", "all"]:
            for event in self.replay_events(self.msg_topic, start_time, end_time, agent_filter):
                event["type"] = "message"
                events.append(event)
                
        if event_type in ["decision", "all"]:
            for event in self.replay_events(self.decision_topic, start_time, end_time, agent_filter):
                event["type"] = "decision"
                events.append(event)
                
        # Sort by timestamp
        events.sort(key=lambda x: x["timestamp"])
        return events

    def configure_retention(self, topic: str, retention_ms: int) -> bool:
        """
        Configure retention policy for a topic.
        Note: This usually requires Admin API and specific permissions.
        We provide it as a placeholder or using AdminClient if available.
        """
        try:
            from confluent_kafka.admin import ConfigResource, ConfigSource
            
            admin_client = self.kafka_bus._producer_config and self.kafka_bus.create_topics.__self__.enabled and \
                (hasattr(self.kafka_bus, 'create_temporary_consumer') and True) # Just checking if we can get config
            
            # Since kafka_bus hides AdminClient creation, we need to instantiate it here
            from confluent_kafka.admin import AdminClient
            
            # Re-use config from kafka_bus (hacky access)
            conf = self.kafka_bus._producer_config
            if not conf:
                return False
                
            a_client = AdminClient(conf)
            
            resource = ConfigResource("topic", topic)
            resource.set_config("retention.ms", str(retention_ms))
            
            fs = a_client.alter_configs([resource])
            
            # Wait for result
            for res, f in fs.items():
                f.result() # Raises exception on failure
                
            logger.info(f"Retention policy updated for {topic} to {retention_ms}ms")
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure retention: {e}")
            return False

# Global instance
event_log_manager = EventLogManager()
