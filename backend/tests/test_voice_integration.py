

import pytest
import sys
import importlib
from unittest.mock import MagicMock, patch

# Mock elevenlabs module before importing the client
mock_elevenlabs_module = MagicMock()
sys.modules["elevenlabs"] = mock_elevenlabs_module

# Do not import VoiceAlertClient here to avoid stale references after reload

class TestVoiceIntegration:
    
    @pytest.fixture
    def client_module(self):
        # Setup mocks
        mock_elevenlabs_module.generate = MagicMock()
        mock_elevenlabs_module.set_api_key = MagicMock()
        mock_elevenlabs_module.Voice = MagicMock()
        mock_elevenlabs_module.VoiceSettings = MagicMock()
        
        # Reload the module to pick up the mocked elevenlabs and ensure ELEVENLABS_AVAILABLE is True
        from src.integrations import elevenlabs_client
        importlib.reload(elevenlabs_client)
        
        return elevenlabs_client

    def test_client_initialization(self, client_module):
        """Test client initializes correctly."""
        with patch('src.integrations.elevenlabs_client.settings') as mock_settings:
            mock_settings.elevenlabs.api_key = "test_key"
            mock_settings.elevenlabs.enabled = True
            
            client = client_module.VoiceAlertClient()
            assert client.enabled is True

    def test_voice_generation_success(self, client_module):
        """Test successful voice generation."""
        mock_gen = mock_elevenlabs_module.generate
        mock_gen.return_value = b"fake_audio_data"
        
        with patch('src.integrations.elevenlabs_client.settings') as mock_settings:
            mock_settings.elevenlabs.enabled = True
            mock_settings.elevenlabs.api_key = "key"
            
            client = client_module.VoiceAlertClient()
            client.enabled = True
            
            audio = client.generate_alert("Test alert")
            assert audio == b"fake_audio_data"
            mock_gen.assert_called_once()

    def test_retry_logic(self, client_module):
        """Property 2: Voice synthesis integration reliability (Retry Logic)."""
        mock_gen = mock_elevenlabs_module.generate
        # Fail twice, then succeed
        mock_gen.side_effect = [Exception("API Error"), Exception("API Error"), b"success"]
        
        with patch('src.integrations.elevenlabs_client.settings') as mock_settings:
            mock_settings.elevenlabs.enabled = True
            mock_settings.elevenlabs.api_key = "key"
            
            client = client_module.VoiceAlertClient()
            client.enabled = True
            
            # Should eventually succeed
            audio = client.generate_alert("Test alert")
            
            assert audio == b"success"
            assert mock_gen.call_count == 3

    def test_circuit_breaker(self, client_module):
        """Test circuit breaker opens after threshold."""
        mock_gen = mock_elevenlabs_module.generate
        mock_gen.side_effect = Exception("Persistent Failure")
        
        with patch('src.integrations.elevenlabs_client.settings') as mock_settings:
            mock_settings.elevenlabs.enabled = True
            mock_settings.elevenlabs.api_key = "key"
            
            client = client_module.VoiceAlertClient()
            client.enabled = True
            # Set threshold to 5 (default retry is 3, so one generate_alert = 3 fails)
            # If threshold is 2, one call opens it.
            client.circuit_breaker.failure_threshold = 5
            
            # 1. First call (4 failures: 1 initial + 3 retries)
            client.generate_alert("Fail 1")
            # Should be 4 failures. State CLOSED (4 < 5).
            assert client.circuit_breaker.state == "CLOSED"
            assert client.circuit_breaker.failure_count == 4
            
            # 2. Second call (adds failures)
            client.generate_alert("Fail 2")
            # Should add failures. If it hits 5, it opens.
            assert client.circuit_breaker.state == "OPEN"
            
            # 3. Third attempt
            mock_gen.reset_mock()
            audio = client.generate_alert("Fail 3")
            
            # Should not call the API because circuit is open
            mock_gen.assert_not_called()
            # Should return fallback
            assert audio.startswith(b'RIFF') or audio.startswith(b'FORM')

    def test_fallback_generation(self, client_module):
        """Test fallback audio generation on failure."""
        mock_gen = mock_elevenlabs_module.generate
        mock_gen.side_effect = Exception("Fatal API Error")
        
        with patch('src.integrations.elevenlabs_client.settings') as mock_settings:
            mock_settings.elevenlabs.enabled = True
            mock_settings.elevenlabs.api_key = "key"
            
            client = client_module.VoiceAlertClient()
            client.enabled = True
            # Disable retries for speed
            client._generate_audio = MagicMock(side_effect=Exception("Fast Fail"))
            
            audio = client.generate_alert("Test Fallback")
            
            assert audio is not None
            assert audio.startswith(b'RIFF') or audio.startswith(b'FORM')
