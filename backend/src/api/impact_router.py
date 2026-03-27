"""
API Router for business impact and ROI metrics.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

from ..prediction_engine.impact_calculator import impact_calculator

router = APIRouter(prefix="/impact", tags=["impact"])

@router.get("/roi")
async def get_roi_report():
    """Get comprehensive ROI and impact report."""
    try:
        return impact_calculator.generate_roi_report()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics")
async def get_impact_metrics():
    """Get raw impact metrics."""
    try:
        metrics = impact_calculator.get_metrics()
        return {
            "total_savings_usd": metrics.total_cost_savings_usd,
            "downtime_prevented_minutes": metrics.total_prevented_downtime_minutes,
            "intervention_count": metrics.intervention_count,
            "last_updated": metrics.last_updated.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
