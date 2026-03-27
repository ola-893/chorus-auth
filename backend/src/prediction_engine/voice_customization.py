"""
Voice customization and configuration management.
"""
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel

from .voice_script_generator import script_generator
from ..integrations.elevenlabs_client import voice_client
from ..config import settings

logger = logging.getLogger(__name__)

class VoiceProfileConfig(BaseModel):
    voice_id: str
    stability: float = 0.5
    similarity_boost: float = 0.75
    speaking_rate: float = 1.0 # 1.0 is normal speed (simulated via text or settings if API supports)

class TemplateConfig(BaseModel):
    name: str
    text: str
    description: str

class VoiceConfigManager:
    """
    Manages runtime configuration for voice alerts.
    """
    
    def __init__(self):
        self.active_profile = VoiceProfileConfig(
            voice_id=settings.elevenlabs.voice_id
        )
        self.incident_preferences: Dict[str, str] = {} # incident_type -> template_name

    def update_voice_profile(self, config: VoiceProfileConfig):
        """Update the active voice profile."""
        self.active_profile = config
        # Update client default voice if needed
        voice_client.default_voice_id = config.voice_id
        logger.info(f"Updated voice profile: {config.voice_id}")

    def update_template(self, config: TemplateConfig):
        """Update or create a script template."""
        script_generator.add_template(config.name, config.text, config.description)
        logger.info(f"Updated template: {config.name}")

    def get_template(self, name: str) -> Optional[Dict]:
        """Get a template definition."""
        tmpl = script_generator.templates.get(name)
        if tmpl:
            return {
                "name": tmpl.name,
                "text": tmpl.template.template,
                "description": tmpl.description
            }
        return None

    def get_config(self) -> Dict[str, Any]:
        """Get full configuration state."""
        return {
            "profile": self.active_profile.dict(),
            "templates": list(script_generator.templates.keys())
        }

# Global instance
voice_config_manager = VoiceConfigManager()
