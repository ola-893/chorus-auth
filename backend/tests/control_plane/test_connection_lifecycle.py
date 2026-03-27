"""
Connected account lifecycle coverage.
"""
from fastapi.testclient import TestClient

from src.control_plane_app import create_app
from src.control_plane_config import settings
from src.db.bootstrap import create_schema
from src.db.session import SessionLocal
from src.demo.seed import seed_demo_environment


def test_connection_start_callback_refresh_and_disconnect(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_mode", "mock")
    monkeypatch.setattr(settings, "vault_mode", "mock")

    create_schema()
    session = SessionLocal()
    try:
        seed_demo_environment(session, reset_runtime=True)
    finally:
        session.close()

    app = create_app()
    with TestClient(app) as client:
        start = client.post(
            "/api/connections/gmail/start",
            json={
                "redirect_uri": "http://localhost:5173/login/callback",
                "requested_scopes": ["gmail.compose"],
            },
        )
        assert start.status_code == 200
        start_payload = start.json()
        assert start_payload["provider"] == "gmail"
        assert start_payload["mode"] == "mock"
        assert start_payload["authorization_url"] is None

        callback = client.get(
            "/api/connections/callback",
            params={
                "provider": "gmail",
                "auth_session": start_payload["auth_session"],
                "connect_code": "mock-connect-code",
                "redirect_uri": start_payload["redirect_uri"],
            },
        )
        assert callback.status_code == 200
        callback_payload = callback.json()
        assert callback_payload["display_label"] == "Google Workspace Mailbox"
        assert callback_payload["connection_health"] == "healthy"
        assert callback_payload["mode"] == "mock"
        assert callback_payload["granted_scopes"] == ["gmail.compose", "gmail.readonly"]

        refresh = client.post(
            f"/api/connections/{callback_payload['id']}/refresh",
            json={},
        )
        assert refresh.status_code == 200
        assert refresh.json()["connection_health"] == "healthy"

        disconnect = client.delete(f"/api/connections/{callback_payload['id']}")
        assert disconnect.status_code == 200
        assert disconnect.json()["status"] == "disconnected"
        assert disconnect.json()["connection_health"] == "degraded"
