"""
Dashboard summary, action detail, and demo API coverage.
"""
from fastapi.testclient import TestClient

from src.control_plane_app import create_app
from src.db.bootstrap import create_schema
from src.db.session import SessionLocal
from src.demo.seed import seed_demo_environment


def test_dashboard_summary_and_action_detail_surface_new_metadata() -> None:
    create_schema()
    session = SessionLocal()
    try:
        seed_demo_environment(session, reset_runtime=True)
    finally:
        session.close()

    app = create_app()
    with TestClient(app) as client:
        allow = client.post("/api/demo/scenarios/allow").json()
        approval = client.post("/api/demo/scenarios/approval").json()
        allow_action_id = allow["created_action_ids"][0]

        summary = client.get("/api/dashboard/summary")
        assert summary.status_code == 200
        summary_payload = summary.json()
        assert summary_payload["auto_approved_count"] >= 1
        assert summary_payload["approval_requested_count"] >= 1
        assert summary_payload["latest_protected_action"]["id"] == approval["created_action_ids"][0]

        detail = client.get(f"/api/actions/{allow_action_id}/detail")
        assert detail.status_code == 200
        detail_payload = detail.json()
        assert detail_payload["action"]["execution_mode"] == "mock"
        assert detail_payload["action"]["vault_reference"] is not None
        assert detail_payload["execution_record"]["execution_mode"] == "mock"
        assert detail_payload["connection_summary"]["mode"] == "mock"
        assert len(detail_payload["audit_events"]) >= 2


def test_demo_quarantine_flow_and_release_endpoint() -> None:
    create_schema()
    session = SessionLocal()
    try:
        seed_demo_environment(session, reset_runtime=True)
    finally:
        session.close()

    app = create_app()
    with TestClient(app) as client:
        result = client.post("/api/demo/scenarios/quarantine")
        assert result.status_code == 200
        payload = result.json()
        assert payload["final_statuses"] == ["policy_blocked", "quarantined"]

        agents = {agent["name"]: agent for agent in client.get("/api/agents").json()}
        ops = agents["Ops Agent"]
        assert ops["status"] == "quarantined"

        released = client.post(f"/api/agents/{ops['id']}/release-quarantine")
        assert released.status_code == 200
        assert released.json()["status"] == "active"
        assert released.json()["quarantine_reason"] is None
