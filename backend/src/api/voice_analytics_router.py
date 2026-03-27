"""
API Router for voice analytics.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

from ..prediction_engine.voice_analytics import voice_analytics

router = APIRouter(prefix="/voice-analytics", tags=["voice-analytics"])

@router.get("/report")
async def get_analytics_report():
    """Get comprehensive voice analytics report."""
    try:
        report = voice_analytics.generate_report()
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
