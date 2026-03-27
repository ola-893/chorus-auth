import base64
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from src.prediction_engine.models.core import AgentMessage

logger = logging.getLogger(__name__)

class AgentVerseAdapter:
    """
    Adapts AgentVerse raw messages to Chorus AgentMessage objects.
    """
    
    @staticmethod
    def parse_timestamp(ts_str: str) -> datetime:
        """Parses ISO timestamp from AgentVerse."""
        try:
            return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except ValueError:
            logger.warning(f"Invalid timestamp format: {ts_str}, using current time")
            return datetime.utcnow()

    @staticmethod
    def decode_payload(encoded_payload: str) -> Dict[str, Any]:
        """Decodes Base64 payload. Returns dict or raw text wrapped in dict."""
        try:
            decoded_bytes = base64.b64decode(encoded_payload)
            decoded_str = decoded_bytes.decode('utf-8')
            try:
                # Try parsing as JSON first
                return json.loads(decoded_str)
            except json.JSONDecodeError:
                # Fallback to raw text
                return {"text": decoded_str}
        except Exception as e:
            logger.error(f"Failed to decode payload: {e}")
            return {"raw_encoded": encoded_payload, "error": str(e)}

    @classmethod
    def to_chorus_message(cls, av_message: Dict[str, Any], sender_alias: Optional[str] = None) -> AgentMessage:
        """
        Converts an AgentVerse message dict to a Chorus AgentMessage.
        
        Args:
            av_message: The raw JSON from AgentVerse API.
            sender_alias: Optional human-readable name resolved from Almanac.
        """
        envelope = av_message.get("envelope", {})
        uuid = av_message.get("uuid")
        received_at = av_message.get("received_at")
        
        sender = envelope.get("sender", "unknown")
        target = envelope.get("target", "unknown")
        protocol = envelope.get("protocol", "unknown")
        encoded_payload = envelope.get("payload", "")
        
        content = cls.decode_payload(encoded_payload)
        
        # Enrich content with metadata
        content["_agentverse_metadata"] = {
            "uuid": uuid,
            "protocol": protocol,
            "sender_address": sender,
            "sender_alias": sender_alias
        }
        
        return AgentMessage(
            sender_id=sender_alias or sender, # Use alias if available, else address
            receiver_id=target,
            message_type="agentverse_interop", # Generic type for external messages
            content=content,
            timestamp=cls.parse_timestamp(received_at) if received_at else datetime.utcnow()
        )
