"""
ElevenLabs integration client for voice alerts.
"""
import logging
import os
import time
from typing import Optional, Union, Iterator
from datetime import datetime

try:
    from elevenlabs import Voice, VoiceSettings
    from elevenlabs.client import ElevenLabs
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False

from ..config import settings
from ..logging_config import get_agent_logger
from ..error_handling import (
    ChorusError,
    CircuitBreaker,
    retry_with_exponential_backoff
)

agent_logger = get_agent_logger(__name__)
logger = logging.getLogger(__name__)

class ElevenLabsError(ChorusError):
    """Exception for ElevenLabs API errors."""
    pass

class VoiceAlertClient:
    """
    Client for interacting with ElevenLabs API to generate voice alerts.
    """

    def __init__(self):
        self.api_key = settings.elevenlabs.api_key
        self.enabled = settings.elevenlabs.enabled and ELEVENLABS_AVAILABLE
        self.default_voice_id = settings.elevenlabs.voice_id
        self.redis = None
        self.client = None
        
        try:
            from ..prediction_engine.redis_client import RedisClient
            self.redis = RedisClient()
        except Exception:
            logger.warning("Redis unavailable for voice caching")
        
        # Initialize circuit breaker for ElevenLabs
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0,
            expected_exception=ElevenLabsError,
            service_name="elevenlabs"
        )

        if self.enabled:
            if self.api_key:
                try:
                    self.client = ElevenLabs(api_key=self.api_key)
                    logger.info("ElevenLabs client initialized")
                except Exception as e:
                    agent_logger.log_system_error(e, "elevenlabs_client", "init")
                    # self.enabled = False # Don't disable, allow fallback
            else:
                logger.warning("ElevenLabs API key not provided, entering Simulation Mode (fallback TTS)")
                # self.enabled = False # Keep enabled for simulation
        elif not ELEVENLABS_AVAILABLE:
            logger.warning("elevenlabs library not installed, voice generation disabled")

    @retry_with_exponential_backoff(
        max_retries=3,
        base_delay=1.0,
        exceptions=(ElevenLabsError,)
    )
    def _generate_audio(self, text: str, voice_obj: 'Voice') -> bytes:
        """
        Internal method to generate audio with retry and circuit breaker.
        """
        # Check cache
        cache_key = f"voice_cache:{hash(text)}:{voice_obj.voice_id}"
        if self.redis:
            try:
                cached = self.redis.get(cache_key)
                if cached:
                    # Redis returns strings by default, but we store bytes? 
                    # Actually RedisClient wrapper returns string. 
                    pass
            except Exception:
                pass

        @self.circuit_breaker
        def _do_generate():
            try:
                start_time = time.time()
                
                # Use the client instance for generation
                # The generate method returns a generator of bytes, we need to collect it
                audio_generator = self.client.generate(
                    text=text,
                    voice=voice_obj.voice_id, 
                    model=settings.elevenlabs.model_id
                )
                
                # Consume generator to get full audio bytes
                audio_bytes = b"".join(chunk for chunk in audio_generator)
                
                duration = time.time() - start_time
                
                agent_logger.log_agent_action(
                    "INFO",
                    "Voice alert generated successfully",
                    action_type="voice_generation_success",
                    context={
                        "text_length": len(text),
                        "duration": duration,
                        "voice_id": voice_obj.voice_id,
                        "cached": False
                    }
                )
                return audio_bytes
            except Exception as e:
                raise ElevenLabsError(
                    f"Failed to generate voice alert: {str(e)}",
                    component="elevenlabs_client",
                    operation="generate_alert"
                ) from e
        
        return _do_generate()

    def _generate_fallback_audio(self, text: str) -> bytes:
        """
        Generate a fallback audio using local system TTS or simple tone.
        """
        try:
            import subprocess
            import sys
            import tempfile
            
            # Try macOS 'say' command
            if sys.platform == "darwin":
                try:
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
                        temp_path = tf.name
                    
                    # Generate WAV
                    subprocess.run(["say", "-o", temp_path, "--data-format=LEI16@44100", text], check=True, capture_output=True)
                    
                    with open(temp_path, "rb") as f:
                        data = f.read()
                        
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                        
                    agent_logger.log_agent_action(
                        "WARNING", 
                        "Used local TTS (say) fallback", 
                        action_type="voice_fallback_local"
                    )
                    return data
                except Exception as e:
                    logger.warning(f"Local TTS failed: {e}")
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)

            import wave
            import io
            import struct
            import math

            # Generate 1 second of simple tone
            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(44100)
                
                # Generate simple sine wave
                duration = 2.0 # seconds
                volume = 0.5
                for i in range(int(duration * 44100)):
                    value = int(32767.0 * volume * math.sin(2.0 * math.pi * 440.0 * i / 44100.0))
                    data = struct.pack('<h', value)
                    wav_file.writeframesraw(data)
            
            agent_logger.log_agent_action(
                "WARNING",
                "Generated fallback audio due to API failure",
                action_type="voice_fallback_generated"
            )
            return buffer.getvalue()
            
        except Exception as e:
            agent_logger.log_system_error(e, "elevenlabs_client", "generate_fallback_audio")
            return b""

    def generate_alert(
        self, 
        text: str, 
        voice_id: Optional[str] = None,
        stability: float = 0.5,
        similarity_boost: float = 0.75
    ) -> Optional[bytes]:
        """
        Generate a voice alert from text.
        """
        if not self.enabled:
            logger.info("Voice generation disabled, skipping alert generation")
            return None

        # Simulation mode check
        if not self.api_key:
            return self._generate_fallback_audio(text)

        try:
            from elevenlabs import Voice, VoiceSettings
            
            voice = Voice(
                voice_id=voice_id or self.default_voice_id,
                settings=VoiceSettings(
                    stability=stability, 
                    similarity_boost=similarity_boost
                )
            )
            result = self._generate_audio(text, voice)
            
            return result
            
        except Exception as e:
            agent_logger.log_system_error(e, "elevenlabs_client", "generate_alert_primary_failed")
            # Fallback
            return self._generate_fallback_audio(text)

    def save_audio_file(self, audio_data: bytes, incident_id: str) -> Optional[str]:
        """
        Save audio data to a file.
        
        Args:
            audio_data: The audio bytes.
            incident_id: Identifier for the incident.
            
        Returns:
            Path to the saved file or None.
        """
        if not audio_data:
            return None
            
        try:
            # Create alerts directory if not exists
            alerts_dir = os.path.join(os.getcwd(), "backend", "alerts")
            os.makedirs(alerts_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"alert_{timestamp}_{incident_id}.wav" # Prefer .wav for fallback
            filepath = os.path.join(alerts_dir, filename)
            
            # Using standard file write for bytes since 'save' from elevenlabs might not be imported or reliable with raw bytes from fallback
            with open(filepath, "wb") as f:
                f.write(audio_data)
            
            logger.info(f"Saved voice alert to {filepath}")
            return filepath
            
        except Exception as e:
            agent_logger.log_system_error(e, "elevenlabs_client", "save_audio_file")
            return None

    def cleanup_old_files(self):
        """Delete audio files older than max_audio_age_days."""
        try:
            alerts_dir = settings.elevenlabs.audio_storage_path
            if not os.path.exists(alerts_dir):
                return
                
            now = time.time()
            max_age = settings.elevenlabs.max_audio_age_days * 86400
            
            count = 0
            for f in os.listdir(alerts_dir):
                fp = os.path.join(alerts_dir, f)
                if os.path.isfile(fp):
                    if now - os.path.getmtime(fp) > max_age:
                        os.remove(fp)
                        count += 1
            
            if count > 0:
                logger.info(f"Cleaned up {count} old audio files")
                
        except Exception as e:
            agent_logger.log_system_error(e, "elevenlabs_client", "cleanup")

# Global instance
voice_client = VoiceAlertClient()