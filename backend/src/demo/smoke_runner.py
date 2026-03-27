"""
Executable smoke runner for the seeded auth control plane demo.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from ..control_plane_app import create_app
from ..db.bootstrap import create_schema
from ..db.session import SessionLocal
from .seed import seed_demo_environment


def run_smoke() -> dict[str, str]:
    """Execute the allow, approval, and quarantine demo story."""
    create_schema()
    session = SessionLocal()
    try:
        seed_demo_environment(session, reset_runtime=True)
    finally:
        session.close()

    app = create_app()

    with TestClient(app) as client:
        agents = {agent["name"]: agent for agent in client.get("/api/agents").json()}
        assistant = agents["Assistant Agent"]
        builder = agents["Builder Agent"]
        ops = agents["Ops Agent"]

        allow_response = client.post(
            "/api/actions",
            json={
                "agent_id": assistant["id"],
                "provider": "gmail",
                "capability_name": "gmail.draft.create",
                "payload": {
                    "to": ["judge@authorizedtoact.dev"],
                    "subject": "Delegated draft",
                    "body": "Prepared by Chorus.",
                },
            },
        )
        allow_action = allow_response.json()

        approval_response = client.post(
            "/api/actions",
            json={
                "agent_id": builder["id"],
                "provider": "github",
                "capability_name": "github.issue.create",
                "payload": {
                    "repository": "chorus/secure-demo",
                    "title": "Review approval workflow",
                    "body": "Opened during smoke coverage.",
                },
            },
        )
        approval_action = approval_response.json()
        pending_approval = next(
            item for item in client.get("/api/approvals").json() if item["status"] == "pending"
        )
        approved_item = client.post(
            f"/api/approvals/{pending_approval['id']}/approve",
            json={"reason": "Smoke runner approval"},
        ).json()

        first_block = client.post(
            "/api/actions",
            json={
                "agent_id": ops["id"],
                "provider": "github",
                "capability_name": "github.pull_request.merge",
                "payload": {
                    "repository": "chorus/secure-demo",
                    "pull_request_number": 18,
                    "summary": "Initial sensitive attempt",
                },
            },
        ).json()
        second_block = client.post(
            "/api/actions",
            json={
                "agent_id": ops["id"],
                "provider": "github",
                "capability_name": "github.pull_request.merge",
                "payload": {
                    "repository": "chorus/secure-demo",
                    "pull_request_number": 18,
                    "summary": "Repeated sensitive attempt",
                },
            },
        ).json()
        ops_after = client.get(f"/api/agents/{ops['id']}").json()

    return {
        "allow_status": allow_action["status"],
        "approval_status": approval_action["status"],
        "approved_queue_status": approved_item["status"],
        "first_block_status": first_block["status"],
        "second_block_status": second_block["status"],
        "ops_agent_status": ops_after["status"],
    }


def main() -> None:
    """Run the smoke flow and print its key outcomes."""
    results = run_smoke()
    for key, value in results.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()

