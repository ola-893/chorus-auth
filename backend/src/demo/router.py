"""
Demo routes for reset and scenario execution.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..auth.adapters import extract_bearer_token
from ..auth.dependencies import get_current_user
from ..db import get_session
from ..db.models import User
from .schemas import DemoResetResponse, ScenarioRunResult
from .service import reset_demo_workspace, run_demo_scenario_with_token

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/reset", response_model=DemoResetResponse)
def post_demo_reset(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> DemoResetResponse:
    """Reset the seeded demo workspace."""
    del current_user
    return reset_demo_workspace(session)


@router.post("/scenarios/{scenario_id}", response_model=ScenarioRunResult)
def post_demo_scenario(
    request: Request,
    scenario_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ScenarioRunResult:
    """Run a seeded demo scenario."""
    try:
        return run_demo_scenario_with_token(
            session,
            current_user,
            scenario_id,
            subject_token=extract_bearer_token(request),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
