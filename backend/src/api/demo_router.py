"""
API Router for demo control and scenario management.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from ..config import settings
from ..prediction_engine.voice_script_generator import script_generator

router = APIRouter(prefix="/demo", tags=["demo"])

class DemoConfig(BaseModel):
    enabled: bool
    audience: str  # technical, business
    scenario: Optional[str] = None

@router.get("/config")
async def get_demo_config():
    return {
        "enabled": settings.demo.mode_enabled,
        "audience": settings.demo.audience,
        "scenario": settings.demo.scenario
    }

@router.post("/config")
async def update_demo_config(config: DemoConfig):
    settings.demo.mode_enabled = config.enabled
    settings.demo.audience = config.audience
    settings.demo.scenario = config.scenario
    return {"status": "updated", "config": config}
