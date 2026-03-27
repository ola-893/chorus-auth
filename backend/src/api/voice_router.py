"""
API Router for voice customization.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict

from ..prediction_engine.voice_customization import (
    voice_config_manager, 
    VoiceProfileConfig, 
    TemplateConfig
)

router = APIRouter(prefix="/voice-config", tags=["voice-config"])

@router.get("/")
async def get_configuration():
    """Get current voice configuration."""
    return voice_config_manager.get_config()

@router.post("/profile")
async def update_profile(config: VoiceProfileConfig):
    """Update voice profile settings."""
    voice_config_manager.update_voice_profile(config)
    return {"status": "updated", "profile": config}

@router.post("/templates")
async def update_template(config: TemplateConfig):
    """Update or create a script template."""
    voice_config_manager.update_template(config)
    return {"status": "updated", "template": config.name}

@router.get("/templates/{name}")
async def get_template(name: str):
    """Get specific template details."""
    tmpl = voice_config_manager.get_template(name)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tmpl
