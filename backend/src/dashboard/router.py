"""
Dashboard routes.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_user
from ..db import get_session
from ..db.models import User
from .schemas import DashboardSummaryResponse
from .service import build_dashboard_summary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> DashboardSummaryResponse:
    """Return summary metrics for the current dashboard view."""
    return build_dashboard_summary(session, current_user)
