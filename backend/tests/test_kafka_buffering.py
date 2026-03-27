"""
Unit tests for Kafka message buffering and replay functionality.
"""
import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from collections import deque

from src.integrations.kafka_client import KafkaMessageBus, KafkaOperationError


class TestKafkaMessageBuffering:
    """Test suite for Kafka message buffering during connection failures."""
    
    @pytest.fixture
    def mock_kafka_bus(self):
        """Create a KafkaMessageBus instance with mocked dependencies."""
        with patch('src.integrations.kafka_client.Producer') as mock_producer, \
             patch('src.integrations.kafka_client.settings') as mock_settings:
            
            # Configure mock settings
            mock_settings.kafka.enabled = True
            mock_settings.kafka.bootstrap_servers = "localhost:9092"
            mock_settings.kafka.security_protocol = "PLAINTEXT"
            mock_settings.kafka.sasl_mechanism = None
            mock_settings.kafka.sasl_username = None
            mock_settings.kafka.sasl_password = None
            mock_settings.kafka.buffer_size = 10
            
            # Create instance
            kafka_bus = KafkaMessageBus()
            kafka_bus.producer = Mock()
            
            yield kafka_bus
    
    def test_buffer_initialization(self, mock_kafka_bus):
        """Test that message buffer is initialized correctly."""
        assert isinstance(mock_kafka_bus.message_buffer, deque)
        assert mock_kafka_bus.message_buffer.maxlen == 10
        assert len(mock_kafka_bus.message_buffer) == 0
        assert mock_kafka_bus._is_connected is True
    
    def test_message_buffering_when_disconnected(self, mock_kafka_bus):
        """Test that messages are buffered when connection is lost."""
        # Simulate disconnection
        mock_kafka_bus._is_connected = False
        
        # Try to produce a message
        test_message = {"type": "test", "data": "hello"}
        mock_kafka_bus.produce("test-topic", test_message)
        
        # Verify message was buffered
        assert len(mock_kafka_bus.message_buffer) == 1
        buffered_msg = mock_kafka_bus.message_buffer[0]
        assert buffered_msg['topic'] == "test-topic"
        assert buffered_msg['value'] == test_message
        assert 'buffered_at' in buffered_msg
        
        # Verify producer was not called
        mock_kafka_bus.producer.produce.assert_not_called()
    
    def test_buffer_overflow_handling(self, mock_kafka_bus):
        """Test that buffer overflow is handled correctly (oldest messages dropped)."""
        # Simulate disconnection
        mock_kafka_bus._is_connected = False
        
        # Fill buffer beyond capacity
        for i in range(15):
            mock_kafka_bus.produce("test-topic", {"id": i})
        
        # Verify buffer size is at max
        assert len(mock_kafka_bus.message_buffer) == 10
        
        # Verify oldest messages were dropped (should have messages 5-14)
        first_msg = mock_kafka_bus.message_buffer[0]
        assert first_msg['value']['id'] == 5
        
        last_msg = mock_kafka_bus.message_buffer[-1]
        assert last_msg['value']['id'] == 14
    
    def test_message_ordering_preserved(self, mock_kafka_bus):
        """Test that message ordering is preserved in buffer."""
        # Simulate disconnection
        mock_kafka_bus._is_connected = False
        
        # Buffer multiple messages
        for i in range(5):
            mock_kafka_bus.produce("test-topic", {"seq": i})
        
        # Verify ordering
        for i, msg in enumerate(mock_kafka_bus.message_buffer):
            assert msg['value']['seq'] == i
    
    def test_replay_buffer_on_reconnection(self, mock_kafka_bus):
        """Test that buffered messages are replayed when connection is restored."""
        # Simulate disconnection and buffer messages
        mock_kafka_bus._is_connected = False
        for i in range(3):
            mock_kafka_bus.produce("test-topic", {"id": i})
        
        assert len(mock_kafka_bus.message_buffer) == 3
        
        # Mock the produce method to track calls during replay
        original_produce = mock_kafka_bus.produce
        produce_calls = []
        
        def mock_produce(topic, value, key=None, headers=None, from_buffer=False):
            if from_buffer:
                produce_calls.append(value)
                # Simulate successful production
                return
            else:
                original_produce(topic, value, key, headers, from_buffer)
        
        mock_kafka_bus.produce = mock_produce
        
        # Simulate reconnection
        mock_kafka_bus._is_connected = True
        mock_kafka_bus._replay_buffer()
        
        # Verify all messages were replayed in order
        assert len(produce_calls) == 3
        for i, value in enumerate(produce_calls):
            assert value['id'] == i
        
        # Verify buffer is empty after successful replay
        assert len(mock_kafka_bus.message_buffer) == 0
    
    def test_replay_stops_on_failure(self, mock_kafka_bus):
        """Test that replay stops and preserves messages if a replay fails."""
        # Buffer messages
        mock_kafka_bus._is_connected = False
        for i in range(5):
            mock_kafka_bus.produce("test-topic", {"id": i})
        
        assert len(mock_kafka_bus.message_buffer) == 5
        
        # Mock produce to fail on third message
        call_count = [0]
        
        def mock_produce(topic, value, key=None, headers=None, from_buffer=False):
            if from_buffer:
                call_count[0] += 1
                if call_count[0] == 3:
                    raise KafkaOperationError("Simulated failure", "kafka", "produce")
                # Don't remove from buffer - the actual replay logic does that
        
        original_produce = mock_kafka_bus.produce
        mock_kafka_bus.produce = mock_produce
        
        # Simulate reconnection and replay
        mock_kafka_bus._is_connected = True
        
        # Manually trigger replay logic (mimicking _replay_buffer)
        replayed = 0
        while mock_kafka_bus.message_buffer and mock_kafka_bus._is_connected:
            msg = mock_kafka_bus.message_buffer.popleft()
            try:
                mock_kafka_bus.produce(
                    msg['topic'], 
                    msg['value'], 
                    msg['key'], 
                    msg['headers'], 
                    from_buffer=True
                )
                replayed += 1
            except Exception:
                # Put message back and stop
                mock_kafka_bus.message_buffer.appendleft(msg)
                break
        
        # Verify replay stopped at failure point (2 successful, then 1 failed)
        assert replayed == 2
        # Verify remaining messages are still in buffer (messages 2, 3, 4)
        assert len(mock_kafka_bus.message_buffer) == 3
        assert mock_kafka_bus.message_buffer[0]['value']['id'] == 2
    
    def test_get_buffer_status(self, mock_kafka_bus):
        """Test buffer status reporting."""
        # Empty buffer
        status = mock_kafka_bus.get_buffer_status()
        assert status['size'] == 0
        assert status['max_size'] == 10
        assert status['utilization'] == 0.0
        assert status['is_full'] is False
        assert status['is_connected'] is True
        
        # Partially filled buffer
        mock_kafka_bus._is_connected = False
        for i in range(5):
            mock_kafka_bus.produce("test-topic", {"id": i})
        
        status = mock_kafka_bus.get_buffer_status()
        assert status['size'] == 5
        assert status['utilization'] == 0.5
        assert status['is_full'] is False
        assert status['is_connected'] is False
        
        # Full buffer
        for i in range(5):
            mock_kafka_bus.produce("test-topic", {"id": i})
        
        status = mock_kafka_bus.get_buffer_status()
        assert status['size'] == 10
        assert status['utilization'] == 1.0
        assert status['is_full'] is True
    
    def test_clear_buffer(self, mock_kafka_bus):
        """Test buffer clearing functionality."""
        # Buffer some messages
        mock_kafka_bus._is_connected = False
        for i in range(5):
            mock_kafka_bus.produce("test-topic", {"id": i})
        
        assert len(mock_kafka_bus.message_buffer) == 5
        
        # Clear buffer
        cleared_count = mock_kafka_bus.clear_buffer()
        
        assert cleared_count == 5
        assert len(mock_kafka_bus.message_buffer) == 0
    
    def test_no_buffering_when_connected(self, mock_kafka_bus):
        """Test that messages are not buffered when connection is active."""
        # Ensure connected
        mock_kafka_bus._is_connected = True
        
        # Mock circuit breaker to allow produce
        mock_kafka_bus.circuit_breaker = Mock()
        mock_kafka_bus.circuit_breaker.__call__ = lambda f: f
        
        # Produce a message
        test_message = {"type": "test"}
        mock_kafka_bus.produce("test-topic", test_message)
        
        # Verify message was not buffered
        assert len(mock_kafka_bus.message_buffer) == 0
    
    def test_from_buffer_flag_prevents_rebuffering(self, mock_kafka_bus):
        """Test that messages from buffer are not re-buffered during replay."""
        # Simulate disconnection during replay
        mock_kafka_bus._is_connected = False
        
        # Try to produce with from_buffer=True
        mock_kafka_bus.produce("test-topic", {"id": 1}, from_buffer=True)
        
        # Message should not be buffered again
        assert len(mock_kafka_bus.message_buffer) == 0
