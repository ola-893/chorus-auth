
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import time
import threading
from src.integrations.datadog_client import DatadogClient

class TestServiceResilience:
    """
    Property 3: Service resilience and fallback effectiveness.
    Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5
    """

    @patch('src.integrations.datadog_client.settings')
    def test_datadog_buffering(self, mock_settings):
        """Verify Datadog metrics are buffered when offline and flushed later."""
        mock_settings.datadog.enabled = True
        mock_settings.datadog.api_key = "test"
        mock_settings.datadog.app_key = "test"
        mock_settings.environment.value = "test"
        
        client = DatadogClient()
        client.metrics_api = MagicMock()
        client.logs_api = MagicMock()
        
        # Stop auto-flush for testing
        client.running = False
        if client.flush_thread:
            client.flush_thread.join(timeout=1.0)
            
        # Queue metrics
        client.send_metric("test.metric", 1.0)
        client.send_metric("test.metric", 2.0)
        
        assert len(client.metric_buffer) == 2
        
        # Manually flush
        client._flush_buffers()
        
        assert len(client.metric_buffer) == 0
        assert client.metrics_api.submit_metrics.call_count == 2

        @patch('src.integrations.elevenlabs_client.settings')
        @patch('src.integrations.elevenlabs_client.generate', create=True)
        def test_elevenlabs_fallback(self, mock_generate, mock_settings):
            """Verify fallback to local generation on API failure."""
            from src.integrations.elevenlabs_client import VoiceAlertClient
        
            mock_settings.elevenlabs.enabled = True
            mock_settings.elevenlabs.api_key = "test"
            
            # Ensure fallback generation is possible
            with patch('src.integrations.elevenlabs_client.ELEVENLABS_AVAILABLE', True):
                client = VoiceAlertClient()
                client.enabled = True # Force enable after init check
            
                # Simulate API failure
                mock_generate.side_effect = Exception("API Error")
                
                # Mock the fallback generator to avoid actual system calls
                with patch.object(client, '_generate_fallback_audio') as mock_fallback:
                    mock_fallback.return_value = b"beep"
                    
                    result = client.generate_alert("Test Alert")
                    
                    assert result == b"beep"
                    mock_fallback.assert_called_once()
    @patch('src.prediction_engine.gemini_client.settings')
    @patch('google.genai.Client')
    def test_gemini_resilience(self, mock_genai_client, mock_settings):
        """Verify Gemini client handles failures gracefully."""
        from src.prediction_engine.gemini_client import GeminiClient
    
        mock_settings.gemini.api_key = "test"
        client = GeminiClient()
        
        # Ensure internal client is using the mock we expect/configure
        # GeminiClient.__init__ sets self._client
        # We can just override it to be sure
        client._client = MagicMock()
        
        # Mock generate_content to fail
        # The code calls self._client.generate_content(prompt)
        client._client.generate_content.side_effect = Exception("API Error")
        
        # Should return None (or safe fallback) instead of crashing
        # Must pass non-empty list with valid intention structure
        mock_intention = MagicMock()
        mock_intention.agent_id = "agent_1"
        mock_intention.resource_type = "cpu"
        mock_intention.requested_amount = 10
        mock_intention.priority_level = 1
        
        # When mocking failure, we expect it to return fallback result, not None
        result = client.analyze_conflict_risk([mock_intention])
        assert result is not None
        assert "Fallback detection" in result.predicted_failure_mode
        assert result.confidence_level == 0.5

    def test_gemini_parsing_resilience(self):
        """Verify parsing handles invalid responses gracefully."""
        from src.prediction_engine.gemini_client import GeminiClient
        from src.prediction_engine.analysis_parser import ConflictAnalysisParser
        
        # Test parser directly for exceptions
        parser = ConflictAnalysisParser()
        
        # Test with empty response
        with pytest.raises(ValueError):
            parser.parse_conflict_analysis("")
            
        # Test with garbage response
        with pytest.raises(ValueError):
            parser.parse_conflict_analysis("This is not JSON or structured data")
            
        # Verify client handles parsing failure by falling back
        with patch('src.prediction_engine.gemini_client.settings') as mock_settings:
            mock_settings.gemini.api_key = "test"
            client = GeminiClient()
            client._client = MagicMock()
            
            mock_response = MagicMock()
            type(mock_response).text = PropertyMock(return_value="Invalid")
            client._client.generate_content.return_value = mock_response
            
            mock_intention = MagicMock()
            mock_intention.agent_id = "agent_1"
            mock_intention.resource_type = "cpu"
            mock_intention.requested_amount = 10
            
            # Should fall back
            result = client.analyze_conflict_risk([mock_intention])
            assert result is not None
            assert "Fallback" in result.predicted_failure_mode
