
import pytest
from hypothesis import given, strategies as st
from unittest.mock import patch

from src.prediction_engine.voice_customization import VoiceConfigManager, VoiceProfileConfig, TemplateConfig
from src.prediction_engine.voice_script_generator import script_generator

class TestPropertyVoiceCustomization:
    
    @given(st.text(min_size=1), st.floats(min_value=0.0, max_value=1.0))
    def test_profile_update_persistence(self, voice_id, stability):
        """
        Property 6: Voice alert customization effectiveness.
        Updates to voice profile should be immediately reflected in the manager state.
        """
        manager = VoiceConfigManager()
        
        config = VoiceProfileConfig(
            voice_id=voice_id,
            stability=stability,
            similarity_boost=0.5
        )
        
        manager.update_voice_profile(config)
        
        current = manager.get_config()["profile"]
        assert current["voice_id"] == voice_id
        assert current["stability"] == stability

    @given(st.text(min_size=1), st.text(min_size=1))
    def test_template_customization(self, name, text):
        """Test dynamic template updates."""
        manager = VoiceConfigManager()
        
        # Ensure name doesn't conflict with Python template syntax if using ${}
        # For this property test we just want to ensure registry updates
        safe_name = f"custom_{name}".replace(" ", "_")
        
        config = TemplateConfig(
            name=safe_name,
            text=text,
            description="Test template"
        )
        
        manager.update_template(config)
        
        # Verify it exists in generator
        assert safe_name in script_generator.templates
        assert script_generator.templates[safe_name].template.template == text
