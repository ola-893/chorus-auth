"""
Seeded demo scenario service used by APIs and smoke coverage.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..actions.schemas import ActionRequestCreate
from ..actions.service import action_request_service
from ..db.models import Agent, User
from .schemas import DemoResetResponse, ScenarioRunResult
from .seed import seed_demo_environment


def reset_demo_workspace(session: Session) -> DemoResetResponse:
    """Reset the seeded demo workspace to a clean state."""
    summary = seed_demo_environment(session, reset_runtime=True)
    return DemoResetResponse(**summary)


def run_demo_scenario(session: Session, user: User, scenario_id: str) -> ScenarioRunResult:
    """Run one seeded demo scenario and return the created actions."""
    return run_demo_scenario_with_token(session, user, scenario_id, subject_token=None)


def run_demo_scenario_with_token(
    session: Session,
    user: User,
    scenario_id: str,
    *,
    subject_token: str | None,
) -> ScenarioRunResult:
    """Run one seeded demo scenario and return the created actions."""
    agents = {
        agent.name: agent
        for agent in session.scalars(select(Agent).where(Agent.owner_user_id == user.id)).all()
    }
    created_actions = []

    if scenario_id == "allow":
        created_actions.append(
            action_request_service.create_action(
                session,
                user,
                ActionRequestCreate(
                    agent_id=agents["Assistant Agent"].id,
                    provider="gmail",
                    capability_name="gmail.draft.create",
                    payload={
                        "to": ["judge@authorizedtoact.dev"],
                        "subject": "Delegated draft",
                        "body": "Prepared by Chorus.",
                    },
                ),
                subject_token=subject_token,
            )
        )
    elif scenario_id == "approval":
        created_actions.append(
            action_request_service.create_action(
                session,
                user,
                ActionRequestCreate(
                    agent_id=agents["Builder Agent"].id,
                    provider="github",
                    capability_name="github.issue.create",
                    payload={
                        "repository": "chorus/secure-demo",
                        "title": "Review approval workflow",
                        "body": "Opened through the demo scenario runner.",
                    },
                ),
                subject_token=subject_token,
            )
        )
    elif scenario_id == "quarantine":
        created_actions.append(
            action_request_service.create_action(
                session,
                user,
                ActionRequestCreate(
                    agent_id=agents["Ops Agent"].id,
                    provider="github",
                    capability_name="github.pull_request.merge",
                    payload={
                        "repository": "chorus/secure-demo",
                        "pull_request_number": 18,
                        "summary": "Initial sensitive attempt",
                    },
                ),
                subject_token=subject_token,
            )
        )
        created_actions.append(
            action_request_service.create_action(
                session,
                user,
                ActionRequestCreate(
                    agent_id=agents["Ops Agent"].id,
                    provider="github",
                    capability_name="github.pull_request.merge",
                    payload={
                        "repository": "chorus/secure-demo",
                        "pull_request_number": 18,
                        "summary": "Repeated sensitive attempt",
                    },
                ),
                subject_token=subject_token,
            )
        )
    else:
        raise ValueError(f"Unsupported scenario: {scenario_id}")

    return ScenarioRunResult(
        scenario_id=scenario_id,
        created_action_ids=[item.id for item in created_actions],
        final_statuses=[item.status.value for item in created_actions],
        highlight_action_id=created_actions[-1].id if created_actions else None,
    )
