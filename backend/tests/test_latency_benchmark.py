
import time
import unittest
from unittest.mock import MagicMock, patch
from src.integrations.elevenlabs_client import VoiceAlertClient

class TestVoiceLatency(unittest.TestCase):
    def test_latency_optimization(self):
        """Verify latency parameters are passed to generation call."""
        with patch('src.integrations.elevenlabs_client.settings') as mock_settings:
            mock_settings.elevenlabs.enabled = True
            mock_settings.elevenlabs.api_key = "key"
            mock_settings.elevenlabs.voice_id = "test_voice_id" # Needs string, not MagicMock
            mock_settings.elevenlabs.model_id = "eleven_turbo_v2"
            
            # Create client with mocks
            client = VoiceAlertClient()
            client.enabled = True
            client.redis = MagicMock() # Mock redis to skip cache check
            client.redis.get.return_value = None
            
            # Mock the generate function - note: we patch where it is used, not defined, or patch the module
            # Since client imports generate, we patch it there IF it's in global scope, 
            # BUT we just saw it's not exposed as attribute.
            # It's imported as 'from elevenlabs import generate' inside the try block.
            # If ELEVENLABS_AVAILABLE is false (like in test environment without package), it might not be there.
            
            # Let's mock the module 'src.integrations.elevenlabs_client.generate'
            # We need to ensure the module has the attribute before patching or use create=True
            with patch('src.integrations.elevenlabs_client.generate', create=True) as mock_gen:
                mock_gen.return_value = b"audio"
                
                client.generate_alert("Test alert")
                
                # Verify latency=3 was passed
                mock_gen.assert_called_with(
                    text="Test alert",
                    voice=unittest.mock.ANY,
                    model="eleven_turbo_v2",
                    latency=3
                )
                print("\n✅ Latency optimization parameter verified")

if __name__ == '__main__':
    unittest.main()

