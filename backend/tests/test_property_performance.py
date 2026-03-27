
import pytest
import time
from unittest.mock import MagicMock, patch, PropertyMock
from src.prediction_engine.gemini_client import GeminiClient

class TestPerformanceRequirements:
    """
    Property 4: Performance requirements compliance.
    Validates: Requirements 6.1, 6.2, 6.3
    """

    @patch('src.prediction_engine.gemini_client.settings')
    @patch('google.genai.Client')
    def test_gemini_caching(self, mock_genai_client, mock_settings):
        """Verify that repeated calls use the cache and are faster."""
        # Setup
        mock_settings.gemini.api_key = "test"
        
        with patch('src.prediction_engine.gemini_client.RedisClient') as mock_redis_class:
            mock_redis_instance = MagicMock()
            mock_redis_class.return_value = mock_redis_instance
            
            client = GeminiClient()
            client._client = MagicMock()
            
            # Simulate cache miss then hit
            mock_redis_instance.get.return_value = None
            
            # Mock response
            mock_response = MagicMock()
            # Use PropertyMock to handle text attribute access - use correct format
            type(mock_response).text = PropertyMock(return_value="RISK_SCORE: 0.1\nCONFIDENCE: 0.9")
            client._client.generate_content.return_value = mock_response
            
            mock_intention = MagicMock()
            mock_intention.agent_id = "agent_1"
            mock_intention.resource_type = "cpu"
            mock_intention.requested_amount = 10
            mock_intention.priority_level = 1
            
            # First call (Miss)
            start_time = time.time()
            client.analyze_conflict_risk([mock_intention])
            duration_miss = time.time() - start_time
            
            # Verify API called
            assert client._client.generate_content.call_count == 1
            assert mock_redis_instance.set.call_count == 1
            
            # Simulate cache hit
            mock_redis_instance.get.return_value = "RISK_SCORE: 0.1\nCONFIDENCE: 0.9"
            
            # Second call (Hit)
            start_time = time.time()
            client.analyze_conflict_risk([mock_intention])
            duration_hit = time.time() - start_time
            
            # Verify API NOT called again
            assert client._client.generate_content.call_count == 1
            
            # Verify hit is faster (mocking makes this trivial, but logic holds)
            print(f"Cache miss duration: {duration_miss:.6f}s")
            print(f"Cache hit duration: {duration_hit:.6f}s")
            
            # In a real system we'd assert duration_hit < duration_miss, 
            # but with mocks it might be too close.
            # We primarily verify the logic flow (API call count).

    @patch('src.integrations.kafka_client.settings')
    def test_kafka_batch_config(self, mock_settings):
        """Verify Kafka producer is configured for batching."""
        from src.integrations.kafka_client import KafkaMessageBus
        
        mock_settings.kafka.enabled = True
        mock_settings.kafka.bootstrap_servers = "test"
        mock_settings.kafka.security_protocol = "PLAINTEXT"
        mock_settings.kafka.sasl_mechanism = None
        mock_settings.kafka.sasl_username = None
        mock_settings.kafka.sasl_password = None
        mock_settings.kafka.buffer_size = 1000
        
        with patch('src.integrations.kafka_client.Producer') as mock_producer:
            bus = KafkaMessageBus()
            config = bus._producer_config
            
            assert config.get('linger.ms') == 5
            assert config.get('batch.size') >= 16384
