"""
Agent registry and capability grant services.
"""
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..db.enums import ProviderType, RiskLevel
from ..db.models import Agent, AgentCapabilityGrant, Capability, User
from .schemas import AgentCreate, AgentResponse, CapabilityGrantCreate, CapabilityGrantResponse

DEFAULT_CAPABILITIES = [
    {
        "name": "gmail.draft.create",
        "provider": ProviderType.GMAIL,
        "action_type": "draft.create",
        "description": "Create a Gmail draft on behalf of the user.",
        "risk_level_default": RiskLevel.LOW,
    },
    {
        "name": "github.issue.create",
        "provider": ProviderType.GITHUB,
        "action_type": "issue.create",
        "description": "Create a GitHub issue in an approved repository.",
        "risk_level_default": RiskLevel.MEDIUM,
    },
    {
        "name": "github.pull_request.merge",
        "provider": ProviderType.GITHUB,
        "action_type": "pull_request.merge",
        "description": "Merge a GitHub pull request after review and approval.",
        "risk_level_default": RiskLevel.HIGH,
    },
]


def ensure_capability_catalog(session: Session) -> None:
    """Seed the control-plane capability catalog if it is empty or missing items."""
    existing = {
        capability.name: capability
        for capability in session.scalars(select(Capability)).all()
    }

    changed = False
    for item in DEFAULT_CAPABILITIES:
        capability = existing.get(item["name"])
        if capability is None:
            capability = Capability(
                name=item["name"],
                provider=item["provider"],
                action_type=item["action_type"],
                description=item["description"],
                risk_level_default=item["risk_level_default"],
                metadata_json={"seeded": True},
            )
            session.add(capability)
            changed = True
        else:
            capability.provider = item["provider"]
            capability.action_type = item["action_type"]
            capability.description = item["description"]
            capability.risk_level_default = item["risk_level_default"]
            capability.metadata_json = {**capability.metadata_json, "seeded": True}
            changed = True

    if changed:
        session.commit()


def serialize_capability_grant(grant: AgentCapabilityGrant) -> CapabilityGrantResponse:
    """Convert an ORM grant into an API response."""
    return CapabilityGrantResponse(
        id=grant.id,
        capability_id=grant.capability_id,
        capability_name=grant.capability.name,
        provider=grant.capability.provider,
        action_type=grant.capability.action_type,
        risk_level_default=grant.capability.risk_level_default,
        constraints=grant.constraints_json,
    )


def serialize_agent(agent: Agent) -> AgentResponse:
    """Convert an ORM agent into an API response."""
    active_quarantine = next((record for record in agent.quarantine_records if record.active), None)
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        agent_type=agent.agent_type,
        description=agent.description,
        status=agent.status,
        metadata=agent.metadata_json,
        quarantine_reason=active_quarantine.trigger_reason if active_quarantine else None,
        capabilities=[serialize_capability_grant(grant) for grant in agent.capability_grants],
    )


def create_agent(session: Session, user: User, payload: AgentCreate) -> AgentResponse:
    """Create a new agent for the current user."""
    agent = Agent(
        owner_user_id=user.id,
        name=payload.name,
        agent_type=payload.agent_type,
        description=payload.description,
        metadata_json=payload.metadata,
    )
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return serialize_agent(agent)


def list_agents(session: Session, user: User) -> list[AgentResponse]:
    """Return all agents for the current user."""
    agents = session.scalars(
        select(Agent)
        .where(Agent.owner_user_id == user.id)
        .options(
            selectinload(Agent.capability_grants).selectinload(AgentCapabilityGrant.capability),
            selectinload(Agent.quarantine_records),
        )
        .order_by(Agent.created_at.asc())
    ).all()
    return [serialize_agent(agent) for agent in agents]


def get_agent_for_user(session: Session, user: User, agent_id: str) -> Agent:
    """Return an agent belonging to the current user or raise 404."""
    agent = session.scalar(
        select(Agent)
        .where(Agent.id == agent_id, Agent.owner_user_id == user.id)
        .options(
            selectinload(Agent.capability_grants).selectinload(AgentCapabilityGrant.capability),
            selectinload(Agent.quarantine_records),
        )
    )
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    return agent


def grant_capability(
    session: Session,
    user: User,
    agent_id: str,
    payload: CapabilityGrantCreate,
) -> CapabilityGrantResponse:
    """Grant a named capability to an owned agent."""
    ensure_capability_catalog(session)
    agent = get_agent_for_user(session, user, agent_id)
    capability = session.scalar(
        select(Capability).where(Capability.name == payload.capability_name)
    )

    if capability is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Capability not found",
        )

    grant = session.scalar(
        select(AgentCapabilityGrant).where(
            AgentCapabilityGrant.agent_id == agent.id,
            AgentCapabilityGrant.capability_id == capability.id,
        )
    )
    if grant is None:
        grant = AgentCapabilityGrant(
            agent_id=agent.id,
            capability_id=capability.id,
            created_by_user_id=user.id,
            constraints_json=payload.constraints,
        )
        session.add(grant)
    else:
        grant.constraints_json = payload.constraints

    session.commit()
    session.refresh(grant)
    session.refresh(agent)
    return serialize_capability_grant(grant)
