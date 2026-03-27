"""
Seed helpers for a repeatable auth control plane demo workspace.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..agents.service import ensure_capability_catalog
from ..control_plane_config import settings
from ..db.enums import AgentStatus, ConnectedAccountStatus, ProviderType
from ..db.models import (
    ActionRequest,
    Agent,
    AgentCapabilityGrant,
    Capability,
    ConnectedAccount,
    User,
)

DEMO_USER = {
    "email": "demo@chorus.local",
    "display_name": "Chorus Demo User",
    "auth_provider_id": "mock",
    "auth_subject": "mock|demo-user",
    "metadata_json": {"mode": "mock", "seeded": True},
}

DEMO_CONNECTIONS = [
    {
        "provider": ProviderType.GMAIL,
        "external_account_id": "demo-gmail-account",
        "scopes_json": ["gmail.compose", "gmail.readonly"],
        "metadata_json": {"label": "Executive mailbox"},
    },
    {
        "provider": ProviderType.GITHUB,
        "external_account_id": "demo-github-account",
        "scopes_json": ["repo", "issues:write", "pull_requests:write"],
        "metadata_json": {"label": "Engineering repo access"},
    },
]

DEMO_AGENTS = [
    {
        "name": "Assistant Agent",
        "agent_type": "assistant",
        "description": "Drafts routine Gmail updates inside an approved domain boundary.",
        "metadata_json": {"role": "assistant"},
        "capability_name": "gmail.draft.create",
        "constraints": {"allowed_domains": ["authorizedtoact.dev"]},
    },
    {
        "name": "Builder Agent",
        "agent_type": "builder",
        "description": "Opens GitHub issues inside the approved demo repository with human approval.",
        "metadata_json": {"role": "builder"},
        "capability_name": "github.issue.create",
        "constraints": {"repo": "chorus/secure-demo"},
    },
    {
        "name": "Ops Agent",
        "agent_type": "ops",
        "description": "Attempts sensitive repository actions and escalates into quarantine on repeat.",
        "metadata_json": {"role": "ops"},
        "capability_name": "github.pull_request.merge",
        "constraints": {"repo": "chorus/secure-demo"},
    },
]


def seed_demo_environment(session: Session, *, reset_runtime: bool = False) -> dict[str, object]:
    """Ensure the demo user, providers, agents, and capability grants exist."""
    ensure_capability_catalog(session)
    user = _upsert_demo_user(session)

    if reset_runtime:
        _reset_demo_runtime(session, user)

    _upsert_demo_connections(session, user)
    _upsert_demo_agents(session, user)
    session.commit()

    return {
        "user_id": user.id,
        "email": user.email,
        "connection_count": len(DEMO_CONNECTIONS),
        "agent_count": len(DEMO_AGENTS),
    }


def seed_demo_on_startup(session: Session) -> dict[str, object] | None:
    """Seed demo data when configured for startup execution."""
    if not settings.seed_demo or not settings.seed_on_startup:
        return None
    return seed_demo_environment(session, reset_runtime=True)


def _upsert_demo_user(session: Session) -> User:
    user = session.scalar(select(User).where(User.email == DEMO_USER["email"]))
    if user is None:
        user = User(**DEMO_USER)
        session.add(user)
        session.flush()
        return user

    user.display_name = DEMO_USER["display_name"]
    user.auth_provider_id = DEMO_USER["auth_provider_id"]
    user.auth_subject = DEMO_USER["auth_subject"]
    user.metadata_json = {**user.metadata_json, **DEMO_USER["metadata_json"]}
    session.flush()
    return user


def _reset_demo_runtime(session: Session, user: User) -> None:
    agents = session.scalars(
        select(Agent)
        .where(Agent.owner_user_id == user.id)
        .options(selectinload(Agent.quarantine_records))
    ).all()

    for agent in agents:
        agent.status = AgentStatus.ACTIVE
        agent.last_violation_at = None
        agent.quarantined_at = None
        for quarantine in agent.quarantine_records:
            session.delete(quarantine)

    action_requests = session.scalars(
        select(ActionRequest).where(ActionRequest.owner_user_id == user.id)
    ).all()
    for action_request in action_requests:
        session.delete(action_request)

    session.flush()


def _upsert_demo_connections(session: Session, user: User) -> None:
    existing = {
        account.provider: account
        for account in session.scalars(
            select(ConnectedAccount).where(ConnectedAccount.user_id == user.id)
        ).all()
    }

    for connection in DEMO_CONNECTIONS:
        account = existing.get(connection["provider"])
        if account is None:
            account = ConnectedAccount(
                user_id=user.id,
                provider=connection["provider"],
                external_account_id=connection["external_account_id"],
                scopes_json=connection["scopes_json"],
                status=ConnectedAccountStatus.CONNECTED,
                connection_mode=settings.vault_mode,
                metadata_json=connection["metadata_json"],
            )
            session.add(account)
            continue

        account.external_account_id = connection["external_account_id"]
        account.scopes_json = connection["scopes_json"]
        account.status = ConnectedAccountStatus.CONNECTED
        account.connection_mode = settings.vault_mode
        account.metadata_json = connection["metadata_json"]


def _upsert_demo_agents(session: Session, user: User) -> None:
    capabilities = {
        capability.name: capability
        for capability in session.scalars(select(Capability)).all()
    }
    existing_agents = {
        agent.name: agent
        for agent in session.scalars(
            select(Agent)
            .where(Agent.owner_user_id == user.id)
            .options(selectinload(Agent.capability_grants))
        ).all()
    }

    for agent_definition in DEMO_AGENTS:
        agent = existing_agents.get(agent_definition["name"])
        if agent is None:
            agent = Agent(
                owner_user_id=user.id,
                name=agent_definition["name"],
                agent_type=agent_definition["agent_type"],
                description=agent_definition["description"],
                status=AgentStatus.ACTIVE,
                metadata_json=agent_definition["metadata_json"],
            )
            session.add(agent)
            session.flush()
        else:
            agent.agent_type = agent_definition["agent_type"]
            agent.description = agent_definition["description"]
            agent.status = AgentStatus.ACTIVE
            agent.metadata_json = agent_definition["metadata_json"]
            agent.last_violation_at = None
            agent.quarantined_at = None

        capability = capabilities[agent_definition["capability_name"]]
        grant = next(
            (item for item in agent.capability_grants if item.capability_id == capability.id),
            None,
        )
        if grant is None:
            grant = AgentCapabilityGrant(
                agent_id=agent.id,
                capability_id=capability.id,
                created_by_user_id=user.id,
                constraints_json=agent_definition["constraints"],
            )
            session.add(grant)
        else:
            grant.constraints_json = agent_definition["constraints"]
