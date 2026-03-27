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
        allow_action = client.post("/api/demo/scenarios/allow").json()
        approval_action = client.post("/api/demo/scenarios/approval").json()
        pending_approval = next(
            item for item in client.get("/api/approvals").json() if item["status"] == "pending"
        )
        approved_item = client.post(
            f"/api/approvals/{pending_approval['id']}/approve",
            json={"reason": "Smoke runner approval"},
        ).json()
        quarantine_result = client.post("/api/demo/scenarios/quarantine").json()
        first_block = client.get(f"/api/actions/{quarantine_result['created_action_ids'][0]}").json()
        second_block = client.get(f"/api/actions/{quarantine_result['created_action_ids'][1]}").json()
        agents = {agent["name"]: agent for agent in client.get("/api/agents").json()}
        ops_after = agents["Ops Agent"]

    return {
        "allow_status": allow_action["final_statuses"][0],
        "approval_status": approval_action["final_statuses"][0],
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
