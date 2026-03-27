"""
Integration test for Kafka message buffering with circuit breaker.
"""
import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from src.integrations.kafka_client import KafkaMessageBus, KafkaOperationError
from src.error_handling import CircuitBreaker


class TestKafkaBufferingIntegration:
    """Integration tests for Kafka buffering with circuit breaker."""
    
    @pytest.fixture
    def kafka_bus_with_circuit_breaker(self):
        """Create a KafkaMessageBus with a real circuit breaker."""
        with patch('src.integrations.kafka_client.Producer') as mock_producer, \
             patch('src.integrations.kafka_client.settings') as mock_settings:
            
            # Configure mock settings
            mock_settings.kafka.enabled = True
            mock_settings.kafka.bootstrap_servers = "localhost:9092"
            mock_settings.kafka.security_protocol = "PLAINTEXT"
            mock_settings.kafka.sasl_mechanism = None
            mock_settings.kafka.sasl_username = None
            mock_settings.kafka.sasl_password = None
            mock_settings.kafka.buffer_size = 100
            
            # Create instance
            kafka_bus = KafkaMessageBus()
            kafka_bus.producer = Mock()
            
            yield kafka_bus
    
    def test_circuit_breaker_triggers_buffering(self, kafka_bus_with_circuit_breaker):
        """Test that circuit breaker opening triggers message buffering."""
        kafka_bus = kafka_bus_with_circuit_breaker
        
        # Ensure we start connected
        assert kafka_bus._is_connected is True
        assert len(kafka_bus.message_buffer) == 0
        
        # Mock producer to fail
        kafka_bus.producer.produce.side_effect = Exception("Connection failed")
        
        # Try to produce messages - this should trigger circuit breaker
        for i in range(6):  # More than failure_threshold (5)
            try:
                kafka_bus.produce("test-topic", {"id": i})
            except:
                pass
        
        # Circuit breaker should be open now, causing buffering
        # Note: The circuit breaker state change is async, so we may need to wait
        time.sleep(0.1)
        
        # Try to produce more messages - these should be buffered
        kafka_bus.produce("test-topic", {"id": 100})
        kafka_bus.produce("test-topic", {"id": 101})
        
        # At least some messages should be buffered
        assert len(kafka_bus.message_buffer) > 0
    
    def test_buffer_replay_on_circuit_breaker_close(self, kafka_bus_with_circuit_breaker):
        """Test that messages are replayed when circuit breaker closes."""
        kafka_bus = kafka_bus_with_circuit_breaker
        
        # Simulate disconnection by setting state directly
        kafka_bus._is_connected = False
        
        # Buffer some messages
        for i in range(5):
            kafka_bus.produce("test-topic", {"id": i})
        
        assert len(kafka_bus.message_buffer) == 5
        
        # Mock produce to succeed during replay
        produce_calls = []
        
        def mock_produce_success(topic, value, key=None, headers=None, callback=None):
            if callback:
                callback(None, Mock(topic=lambda: topic))
        
        kafka_bus.producer.produce = mock_produce_success
        
        # Simulate reconnection
        kafka_bus._is_connected = True
        kafka_bus._replay_buffer()
        
        # Buffer should be empty after successful replay
        assert len(kafka_bus.message_buffer) == 0
    
    def test_buffer_status_tracking(self, kafka_bus_with_circuit_breaker):
        """Test that buffer status is accurately tracked."""
        kafka_bus = kafka_bus_with_circuit_breaker
        
        # Initial status
        status = kafka_bus.get_buffer_status()
        assert status['size'] == 0
        assert status['utilization'] == 0.0
        assert status['is_full'] is False
        assert status['is_connected'] is True
        
        # Buffer some messages
        kafka_bus._is_connected = False
        for i in range(50):
            kafka_bus.produce("test-topic", {"id": i})
        
        status = kafka_bus.get_buffer_status()
        assert status['size'] == 50
        assert status['utilization'] == 0.5
        assert status['is_full'] is False
        assert status['is_connected'] is False
        
        # Fill buffer completely
        for i in range(50):
            kafka_bus.produce("test-topic", {"id": i + 50})
        
        status = kafka_bus.get_buffer_status()
        assert status['size'] == 100
        assert status['utilization'] == 1.0
        assert status['is_full'] is True
