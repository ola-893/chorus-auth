"""
Auth flow coverage for mock and Auth0-backed session behavior.
"""
from __future__ import annotations

import base64
import json
import time

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi.testclient import TestClient

from src.control_plane_app import create_app
from src.db.bootstrap import create_schema
from src.db.session import SessionLocal
from src.demo.seed import seed_demo_environment
from src.auth.jwt_verifier import jwt_verifier
from src.control_plane_config import settings


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _make_token(private_key: rsa.RSAPrivateKey, payload: dict, kid: str = "test-key") -> str:
    header = {"alg": "RS256", "typ": "JWT", "kid": kid}
    encoded_header = _b64url(json.dumps(header).encode("utf-8"))
    encoded_payload = _b64url(json.dumps(payload).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return f"{encoded_header}.{encoded_payload}.{_b64url(signature)}"


def _jwk_for_private_key(private_key: rsa.RSAPrivateKey, kid: str = "test-key") -> dict:
    public_numbers = private_key.public_key().public_numbers()
    modulus = public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, "big")
    exponent = public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, "big")
    return {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": kid,
        "n": _b64url(modulus),
        "e": _b64url(exponent),
    }


def test_auth_session_reports_signed_out_when_bearer_is_missing(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_mode", "auth0")
    monkeypatch.setattr(settings, "allow_demo_mode", True)

    app = create_app()
    with TestClient(app) as client:
        session = client.get("/api/auth/session")

    assert session.status_code == 200
    payload = session.json()
    assert payload["authenticated"] is False
    assert payload["allow_demo_mode"] is True
    assert payload["user"] is None


def test_auth0_bearer_token_is_verified_and_upserts_user(monkeypatch) -> None:
    create_schema()
    session = SessionLocal()
    try:
        seed_demo_environment(session, reset_runtime=True)
    finally:
        session.close()

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwks = {"keys": [_jwk_for_private_key(private_key)]}
    monkeypatch.setattr(jwt_verifier, "_fetch_jwks", lambda: jwks)
    monkeypatch.setattr(settings, "auth_mode", "auth0")
    monkeypatch.setattr(settings, "auth0_domain", "demo.auth0.local")
    monkeypatch.setattr(settings, "auth0_issuer", "https://demo.auth0.local/")
    monkeypatch.setattr(settings, "auth0_audience", "https://chorus.demo/api")

    token = _make_token(
        private_key,
        {
            "sub": "auth0|judge-user",
            "aud": ["https://chorus.demo/api"],
            "iss": "https://demo.auth0.local/",
            "exp": int(time.time()) + 600,
            "email": "judge@example.com",
            "name": "Judge User",
        },
    )

    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
        session_response = client.get("/api/auth/session", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["email"] == "judge@example.com"
    assert response.json()["auth_subject"] == "auth0|judge-user"

    assert session_response.status_code == 200
    assert session_response.json()["authenticated"] is True
    assert session_response.json()["user"]["display_name"] == "Judge User"


def test_auth_config_exposes_frontend_bootstrap_fields(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_mode", "auth0")
    monkeypatch.setattr(settings, "allow_demo_mode", False)
    monkeypatch.setattr(settings, "auth0_domain", "tenant.us.auth0.com")
    monkeypatch.setattr(settings, "auth0_client_id", "client_123")
    monkeypatch.setattr(settings, "auth0_audience", "https://chorus.demo/api")
    monkeypatch.setattr(settings, "auth0_scope", "openid profile email offline_access")
    monkeypatch.setattr(settings, "auth0_issuer", None)

    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/auth/config")

    assert response.status_code == 200
    payload = response.json()
    assert payload["auth_mode"] == "auth0"
    assert payload["allow_demo_mode"] is False
    assert payload["auth0_client_id"] == "client_123"
    assert payload["auth0_issuer"] == "https://tenant.us.auth0.com/"
    assert payload["callback_path"] == "/login/callback"
