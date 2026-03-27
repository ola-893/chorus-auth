"""
Kafka integration client for message streaming.
"""
import json
import logging
import socket
from typing import Dict, Any, Optional, Callable, List
import time
from collections import deque

try:
    from confluent_kafka import Producer, Consumer, KafkaError, Message, KafkaException
    from confluent_kafka.admin import AdminClient, NewTopic
except ImportError:
    Producer = None
    Consumer = None
    KafkaError = None
    Message = None
    KafkaException = None
    AdminClient = None
    NewTopic = None

from ..config import settings
from ..error_handling import (
    CircuitBreaker, 
    retry_with_exponential_backoff, 
    ChorusError
)
from ..logging_config import get_agent_logger
from ..event_bus import event_bus

agent_logger = get_agent_logger(__name__)

class KafkaOperationError(ChorusError):
    """Exception for Kafka operation errors."""
    pass

class KafkaMessageBus:
    """
    Client for interacting with Confluent Kafka.
    """
    
    def __init__(self):
        """Initialize Kafka client."""
        self.enabled = settings.kafka.enabled
        self.bootstrap_servers = settings.kafka.bootstrap_servers
        self.security_protocol = settings.kafka.security_protocol
        self.sasl_mechanism = settings.kafka.sasl_mechanism
        self.sasl_username = settings.kafka.sasl_username
        self.sasl_password = settings.kafka.sasl_password
        
        self.producer = None
        self.consumer = None
        self._producer_config = {}
        self._consumer_config = {}
        
        # Message buffer for connection failures
        self.message_buffer = deque(maxlen=settings.kafka.buffer_size)
        self._is_connected = True

        def on_breaker_state_change(new_state):
            if new_state == "CLOSED":
                self._is_connected = True
                self._replay_buffer()
            elif new_state == "OPEN":
                self._is_connected = False

        # Define circuit breaker for Kafka operations
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=30.0,
            expected_exception=(KafkaOperationError, Exception),
            service_name="kafka",
            on_state_change=on_breaker_state_change
        )
        
        if self.enabled and Producer:
            self._initialize_config()
            self._initialize_producer()
        
        event_bus.subscribe('circuit_breaker_state_change', self._handle_circuit_breaker_change)

    def _handle_circuit_breaker_change(self, data):
        """Handle circuit breaker state changes from event bus."""
        if data.get('service') == 'kafka':
            if data.get('new_state') == 'CLOSED':
                self._is_connected = True
                self._replay_buffer()
            elif data.get('new_state') == 'OPEN':
                self._is_connected = False
    
    def get_buffer_status(self) -> Dict[str, Any]:
        """
        Get current buffer status.
        
        Returns:
            Dictionary with buffer metrics
        """
        return {
            "size": len(self.message_buffer),
            "max_size": self.message_buffer.maxlen,
            "utilization": len(self.message_buffer) / self.message_buffer.maxlen if self.message_buffer.maxlen > 0 else 0,
            "is_full": len(self.message_buffer) == self.message_buffer.maxlen,
            "is_connected": self._is_connected
        }
    
    def clear_buffer(self) -> int:
        """
        Clear the message buffer.
        
        Returns:
            Number of messages cleared
        """
        count = len(self.message_buffer)
        self.message_buffer.clear()
        agent_logger.log_agent_action(
            "WARNING", 
            f"Cleared {count} messages from buffer", 
            action_type="kafka_buffer_cleared"
        )
        return count
    
    def _replay_buffer(self):
        """
        Replay messages from the buffer when connection is restored.
        Messages are replayed in FIFO order to preserve ordering.
        If replay fails, the message is returned to the front of the buffer.
        """
        if not self._is_connected or not self.message_buffer:
            return
            
        buffer_size = len(self.message_buffer)
        agent_logger.log_agent_action(
            "INFO", 
            f"Replaying {buffer_size} buffered messages.", 
            action_type="kafka_replay_start"
        )
        
        replayed_count = 0
        failed_count = 0
        
        while self.message_buffer and self._is_connected:
            msg = self.message_buffer.popleft()
            try:
                self.produce(
                    msg['topic'], 
                    msg['value'], 
                    msg['key'], 
                    msg['headers'], 
                    from_buffer=True
                )
                replayed_count += 1
            except Exception as e:
                agent_logger.log_system_error(
                    e, 
                    "kafka_client", 
                    "_replay_buffer", 
                    context={
                        "message": msg,
                        "replayed": replayed_count,
                        "remaining": len(self.message_buffer) + 1
                    }
                )
                # If replay fails, put message back at the front and stop
                self.message_buffer.appendleft(msg)
                failed_count += 1
                break
        
        agent_logger.log_agent_action(
            "INFO", 
            f"Finished replaying buffer. Replayed: {replayed_count}, Failed: {failed_count}, Remaining: {len(self.message_buffer)}", 
            action_type="kafka_replay_end"
        )
    
    def _initialize_config(self):
        """Initialize Kafka configuration."""
        base_config = {
            'bootstrap.servers': self.bootstrap_servers,
            'security.protocol': self.security_protocol,
            'client.id': socket.gethostname(),
        }
        
        if self.sasl_mechanism and self.sasl_username and self.sasl_password:
            base_config.update({
                'sasl.mechanism': self.sasl_mechanism,
                'sasl.username': self.sasl_username,
                'sasl.password': self.sasl_password,
            })
        
        # Use optimized configurations from performance optimizer
        try:
            from ..performance_optimizer import kafka_optimizer
            self._producer_config = kafka_optimizer.get_optimized_producer_config()
            self._consumer_config = kafka_optimizer.get_optimized_consumer_config('chorus-backend-group')
        except ImportError:
            # Fallback to basic configuration
            self._producer_config = base_config.copy()
            self._producer_config.update({
                'compression.type': 'lz4',
                'linger.ms': 5,
                'batch.size': 65536,
                'retries': 10,
                'delivery.timeout.ms': 120000,
                'acks': 'all',
                'enable.idempotence': False
            })
            
            self._consumer_config = base_config.copy()
            self._consumer_config.update({
                'group.id': 'chorus-backend-group',
                'auto.offset.reset': 'earliest',
                'enable.auto.commit': False,
                'session.timeout.ms': 30000,
                'fetch.min.bytes': 50000
            })

    def _initialize_producer(self):
        """Initialize Kafka producer."""
        try:
            self.producer = Producer(self._producer_config)
            agent_logger.log_agent_action(
                "INFO",
                "Kafka producer initialized",
                action_type="kafka_init"
            )
        except Exception as e:
            agent_logger.log_system_error(e, "kafka_client", "init_producer")
            self.enabled = False

    @retry_with_exponential_backoff(max_retries=3, base_delay=0.1, exceptions=(KafkaOperationError,))
    def produce(self, topic: str, value: Dict[str, Any], key: Optional[str] = None, headers: Optional[Dict[str, str]] = None, from_buffer: bool = False) -> None:
        """
        Produce a message to a Kafka topic.
        
        Args:
            topic: Target topic
            value: Message body (will be JSON serialized)
            key: Message key (optional)
            headers: Message headers (optional)
            from_buffer: Whether the message is from the replay buffer
        """
        if not self.enabled or not self.producer:
            if settings.kafka.enabled: 
                agent_logger.log_agent_action("WARNING", "Kafka producer not available", action_type="kafka_produce_skipped")
            return

        if not self._is_connected and not from_buffer:
            # Buffer the message for later replay
            buffer_full = len(self.message_buffer) == self.message_buffer.maxlen
            if buffer_full:
                agent_logger.log_agent_action(
                    "WARNING", 
                    f"Kafka message buffer is full ({self.message_buffer.maxlen} messages). Oldest message will be dropped.", 
                    action_type="kafka_buffer_overflow",
                    context={"topic": topic}
                )
            
            self.message_buffer.append({
                'topic': topic, 
                'value': value, 
                'key': key, 
                'headers': headers,
                'buffered_at': time.time()
            })
            
            if not buffer_full:
                agent_logger.log_agent_action(
                    "INFO", 
                    f"Message buffered for topic {topic}. Buffer size: {len(self.message_buffer)}/{self.message_buffer.maxlen}", 
                    action_type="kafka_message_buffered"
                )
            return

        @self.circuit_breaker
        def _do_produce():
            try:
                def delivery_report(err, msg):
                    if err is not None:
                        agent_logger.log_system_error(
                            Exception(f"Message delivery failed: {err}"), 
                            "kafka_client", 
                            "delivery_report",
                            context={"topic": topic}
                        )
                    else:
                        agent_logger.log_agent_action(
                            "INFO",
                            f"Kafka message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}",
                            action_type="kafka_delivery_success",
                            context={"topic": msg.topic(), "partition": msg.partition(), "offset": msg.offset()}
                        )

                json_value = json.dumps(value).encode('utf-8')
                encoded_key = key.encode('utf-8') if key else None
                kafka_headers = [(k, v.encode('utf-8')) for k, v in headers.items()] if headers else None

                self.producer.produce(
                    topic,
                    value=json_value,
                    key=encoded_key,
                    headers=kafka_headers,
                    callback=delivery_report
                )
                
                self.producer.poll(0)
                
            except Exception as e:
                raise KafkaOperationError(
                    f"Failed to produce message to {topic}: {str(e)}",
                    component="kafka_client",
                    operation="produce",
                    context={"topic": topic}
                ) from e

        _do_produce()

    def subscribe(self, topics: List[str]):
        """
        Subscribe consumer to topics.
        """
        if not self.enabled:
            return

        if not self.consumer:
            try:
                self.consumer = Consumer(self._consumer_config)
            except Exception as e:
                agent_logger.log_system_error(e, "kafka_client", "init_consumer")
                return

        try:
            self.consumer.subscribe(topics)
            agent_logger.log_agent_action("INFO", f"Subscribed to topics: {topics}", action_type="kafka_subscribe")
        except Exception as e:
            agent_logger.log_system_error(e, "kafka_client", "subscribe")

    def poll(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """
        Poll for new messages.
        
        Returns:
            Dictionary with message data (value, key, topic, partition, offset) or None
        """
        if not self.consumer:
            return None

        try:
            msg = self.consumer.poll(timeout)
            
            if msg is None:
                return None
            
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    # End of partition event
                    return None
                else:
                    agent_logger.log_system_error(
                        Exception(msg.error()), 
                        "kafka_client", 
                        "poll_error"
                    )
                    return None
            
            # Deserialize value
            try:
                value = json.loads(msg.value().decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Return raw bytes if not JSON
                value = msg.value()
                
            return {
                "value": value,
                "key": msg.key().decode('utf-8') if msg.key() else None,
                "topic": msg.topic(),
                "partition": msg.partition(),
                "offset": msg.offset(),
                "timestamp": msg.timestamp()[1] # (type, timestamp)
            }
            
        except Exception as e:
            agent_logger.log_system_error(e, "kafka_client", "poll")
            return None

    def commit(self, asynchronous: bool = True):
        """Commit offsets."""
        if self.consumer:
            try:
                self.consumer.commit(asynchronous=asynchronous)
            except Exception as e:
                 agent_logger.log_system_error(e, "kafka_client", "commit")

    def close(self):
        """Close producer and consumer."""
        if self.producer:
            self.producer.flush()
        if self.consumer:
            self.consumer.close()

    def flush(self, timeout: float = 10.0) -> int:
        """Flush producer queue."""
        if self.producer:
            return self.producer.flush(timeout)
        return 0

    def create_topics(self, topics: List[str], num_partitions: int = 1, replication_factor: int = 1):
        """
        Create topics if they don't exist.
        
        Args:
            topics: List of topic names
            num_partitions: Number of partitions
            replication_factor: Replication factor
        """
        if not self.enabled or not AdminClient:
            return

        admin_client = AdminClient(self._producer_config)
        
        new_topics = [
            NewTopic(topic, num_partitions=num_partitions, replication_factor=replication_factor)
            for topic in topics
        ]
        
        # Call create_topics to asynchronously create topics.
        fs = admin_client.create_topics(new_topics)

        # Wait for each operation to finish.
        for topic, f in fs.items():
            try:
                f.result()  # The result itself is None
                agent_logger.log_agent_action(
                    "INFO", 
                    f"Topic created: {topic}", 
                    action_type="kafka_topic_create"
                )
            except Exception as e:
                # Continue if topic already exists
                if "TopicExists" in str(e) or (hasattr(e, 'args') and "TOPIC_ALREADY_EXISTS" in str(e.args[0])):
                    pass 
                else:
                    agent_logger.log_system_error(e, "kafka_client", "create_topics", context={"topic": topic})

    def create_temporary_consumer(self, group_id: Optional[str] = None) -> Optional['Consumer']:
        """
        Create a temporary consumer for replay or ad-hoc querying.
        
        Args:
            group_id: Consumer group ID (optional, defaults to random)
            
        Returns:
            Configured Consumer instance or None if Kafka is disabled
        """
        if not self.enabled or not Consumer:
            return None
            
        config = self._consumer_config.copy()
        config['group.id'] = group_id or f"chorus-replay-{int(time.time()*1000)}"
        config['auto.offset.reset'] = 'earliest'
        config['enable.auto.commit'] = False
        
        try:
            return Consumer(config)
        except Exception as e:
            agent_logger.log_system_error(e, "kafka_client", "create_temporary_consumer")
            return None

    def get_topic_offsets_for_time(self, consumer: 'Consumer', topic: str, timestamp: int) -> Dict[Any, Any]:
        """
        Get offsets for a specific timestamp for all partitions of a topic.
        
        Args:
            consumer: Consumer instance to use
            topic: Topic name
            timestamp: Timestamp in milliseconds
            
        Returns:
            Dictionary of TopicPartition -> Offset
        """
        try:
            # Get metadata to find partitions
            metadata = consumer.list_topics(topic)
            if topic not in metadata.topics:
                return {}
                
            partitions = [
                (topic, p) 
                for p in metadata.topics[topic].partitions.keys()
            ]
            
            # Build TopicPartitions with timestamp
            from confluent_kafka import TopicPartition
            timestamps = [
                TopicPartition(topic, p, timestamp) 
                for topic, p in partitions
            ]
            
            # Look up offsets
            offsets = consumer.offsets_for_times(timestamps)
            return offsets
            
        except Exception as e:
            agent_logger.log_system_error(e, "kafka_client", "get_topic_offsets_for_time")
            return {}

# Global instance
kafka_bus = KafkaMessageBus()
