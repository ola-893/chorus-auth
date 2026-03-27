"""
Agent registry API routes.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_user
from ..db import get_session
from ..db.models import User
from .schemas import AgentCreate, AgentResponse, CapabilityGrantCreate, CapabilityGrantResponse
from .service import create_agent, get_agent_for_user, grant_capability, list_agents, release_quarantine, serialize_agent

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentResponse])
def get_agents(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[AgentResponse]:
    """List the current user's agents."""
    return list_agents(session, current_user)


@router.post("", response_model=AgentResponse)
def post_agent(
    payload: AgentCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AgentResponse:
    """Create a new agent."""
    return create_agent(session, current_user, payload)


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AgentResponse:
    """Get a single agent owned by the current user."""
    return serialize_agent(get_agent_for_user(session, current_user, agent_id))


@router.post("/{agent_id}/capability-grants", response_model=CapabilityGrantResponse)
def post_capability_grant(
    agent_id: str,
    payload: CapabilityGrantCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CapabilityGrantResponse:
    """Grant a named capability to an agent."""
    return grant_capability(session, current_user, agent_id, payload)


@router.post("/{agent_id}/release-quarantine", response_model=AgentResponse)
def post_release_quarantine(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AgentResponse:
    """Release an agent from quarantine."""
    return release_quarantine(session, current_user, agent_id)
