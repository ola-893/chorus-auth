
import pytest
from unittest.mock import MagicMock, patch
from src.integration_validator import IntegrationValidator

class TestPropertyIntegrationValidation:
    """
    Property 5: Integration authenticity and completeness.
    Validates: Requirements 4.1, 4.3, 4.5
    """

    @patch('src.integration_validator.settings')
    def test_audit_logging(self, mock_settings):
        """Verify API calls are logged with required metadata."""
        mock_settings.environment.value = "test"
        validator = IntegrationValidator()
        
        validator.log_api_call("gemini", "generate", "success", 120.5)
        
        entry = validator.audit_log[-1]
        assert entry["partner"] == "gemini"
        assert entry["latency_ms"] == 120.5
        assert "timestamp" in entry
        assert entry["environment"] == "test"

    @patch('src.prediction_engine.gemini_client.GeminiClient')
    def test_validation_completeness(self, MockGemini):
        """Verify validation checks all 4 core partners."""
        validator = IntegrationValidator()
        
        # Mock successful checks
        MockGemini.return_value.test_connection.return_value = True
        
        # We assume Datadog/Kafka/ElevenLabs rely on global clients being enabled
        # which depends on settings. We can mock the imports inside the method if needed,
        # but here we rely on the fact that those modules check settings on init.
        # Since we are in a test env, they might be disabled.
        # Let's mock the result dictionary construction indirectly or mock the modules.
        
        with patch('src.integrations.kafka_client.kafka_bus') as mock_kafka:
            mock_kafka.enabled = True
            with patch('src.integrations.elevenlabs_client.voice_client') as mock_voice:
                mock_voice.enabled = True
                with patch('src.integrations.datadog_client.datadog_client') as mock_datadog:
                    mock_datadog.enabled = True
                    
                    results = validator.validate_integrations()
                    
                    assert "gemini" in results
                    assert "datadog" in results
                    assert "kafka" in results
                    assert "elevenlabs" in results
