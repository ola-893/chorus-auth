"""
Smoke coverage for the seeded auth control plane demo.
"""
from fastapi.testclient import TestClient

from src.control_plane_app import create_app
from src.db.bootstrap import create_schema
from src.db.session import SessionLocal
from src.demo.smoke_runner import run_smoke
from src.demo.seed import seed_demo_environment


def test_seeded_demo_flow_covers_allow_approval_and_quarantine() -> None:
    create_schema()
    session = SessionLocal()
    try:
        summary = seed_demo_environment(session, reset_runtime=True)
        assert summary["connection_count"] == 2
        assert summary["agent_count"] == 3
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
                    "body": "Prepared automatically.",
                },
            },
        )
        assert allow_response.status_code == 200
        allow_action = allow_response.json()
        assert allow_action["status"] == "completed"
        assert allow_action["execution_status"] == "succeeded"
        assert allow_action["enforcement_decision"] == "ALLOW"

        approval_response = client.post(
            "/api/actions",
            json={
                "agent_id": builder["id"],
                "provider": "github",
                "capability_name": "github.issue.create",
                "payload": {
                    "repository": "chorus/secure-demo",
                    "title": "Review approval workflow",
                    "body": "Created by the smoke suite.",
                },
            },
        )
        assert approval_response.status_code == 200
        approval_action = approval_response.json()
        assert approval_action["status"] == "pending_approval"
        assert approval_action["enforcement_decision"] == "REQUIRE_APPROVAL"

        approvals = client.get("/api/approvals").json()
        pending = next(item for item in approvals if item["status"] == "pending")
        approved = client.post(
            f"/api/approvals/{pending['id']}/approve",
            json={"reason": "Smoke suite approval"},
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"

        approved_action = client.get(f"/api/actions/{approval_action['id']}").json()
        assert approved_action["status"] == "completed"
        assert approved_action["execution_status"] == "succeeded"

        first_block = client.post(
            "/api/actions",
            json={
                "agent_id": ops["id"],
                "provider": "github",
                "capability_name": "github.pull_request.merge",
                "payload": {
                    "repository": "chorus/secure-demo",
                    "pull_request_number": 18,
                    "summary": "First blocked attempt",
                },
            },
        )
        assert first_block.status_code == 200
        assert first_block.json()["status"] == "policy_blocked"
        assert first_block.json()["enforcement_decision"] == "BLOCK"

        second_block = client.post(
            "/api/actions",
            json={
                "agent_id": ops["id"],
                "provider": "github",
                "capability_name": "github.pull_request.merge",
                "payload": {
                    "repository": "chorus/secure-demo",
                    "pull_request_number": 18,
                    "summary": "Second blocked attempt",
                },
            },
        )
        assert second_block.status_code == 200
        assert second_block.json()["status"] == "quarantined"
        assert second_block.json()["enforcement_decision"] == "QUARANTINE"

        ops_after = client.get(f"/api/agents/{ops['id']}").json()
        assert ops_after["status"] == "quarantined"
        assert "quarantine" in ops_after["quarantine_reason"].lower()

        audit = client.get("/api/audit").json()
        event_types = {event["event_type"] for event in audit}
        assert "action.executed" in event_types
        assert "approval.approved" in event_types
        assert "agent.quarantined" in event_types


def test_smoke_runner_is_repeatable_across_multiple_runs() -> None:
    first = run_smoke()
    second = run_smoke()

    assert first["allow_status"] == "completed"
    assert first["first_block_status"] == "policy_blocked"
    assert first["second_block_status"] == "quarantined"

    assert second["allow_status"] == "completed"
    assert second["first_block_status"] == "policy_blocked"
    assert second["second_block_status"] == "quarantined"
