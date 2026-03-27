"""
Auth adapter implementations for mock and Auth0-backed modes.
"""
from dataclasses import dataclass
from typing import Protocol

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..control_plane_config import settings
from ..db.models import User
from .jwt_verifier import jwt_verifier


@dataclass
class ResolvedIdentity:
    """Normalized identity returned by auth adapters."""

    email: str
    display_name: str
    auth_subject: str
    auth_provider_id: str
    metadata: dict


class AuthAdapter(Protocol):
    """Protocol for resolving the current user."""

    def resolve_identity(self, request: Request) -> ResolvedIdentity:
        """Resolve a request into a normalized identity."""


class MockAuthAdapter:
    """Mock adapter for local demo execution."""

    def resolve_identity(self, request: Request) -> ResolvedIdentity:
        return ResolvedIdentity(
            email="demo@chorus.local",
            display_name="Chorus Demo User",
            auth_subject="mock|demo-user",
            auth_provider_id="mock",
            metadata={"mode": "mock"},
        )


class Auth0AuthAdapter:
    """Bearer-token Auth0 adapter backed by JWKS verification."""

    def resolve_identity(self, request: Request) -> ResolvedIdentity:
        token = extract_bearer_token(request)
        if token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Auth0 bearer token",
            )
        claims = jwt_verifier.verify(token)
        email = claims.email or _fallback_email_for_subject(claims.sub)
        display_name = claims.name or claims.nickname or email

        return ResolvedIdentity(
            email=email,
            display_name=display_name,
            auth_subject=claims.sub,
            auth_provider_id="auth0",
            metadata={"mode": "auth0", "claims": {"aud": claims.claims.get("aud")}},
        )


def get_auth_adapter() -> AuthAdapter:
    """Return the configured auth adapter."""
    if settings.auth_mode == "auth0":
        return Auth0AuthAdapter()
    return MockAuthAdapter()


def resolve_or_create_user(session: Session, request: Request) -> User:
    """Resolve the current request identity and upsert the corresponding user."""
    adapter = get_auth_adapter()
    identity = adapter.resolve_identity(request)

    user = session.scalar(select(User).where(User.auth_subject == identity.auth_subject))
    if user is None:
        user = session.scalar(select(User).where(User.email == identity.email))

    if user is None:
        user = User(
            email=identity.email,
            display_name=identity.display_name,
            auth_provider_id=identity.auth_provider_id,
            auth_subject=identity.auth_subject,
            metadata_json=identity.metadata,
        )
        session.add(user)
    else:
        user.display_name = identity.display_name
        user.auth_provider_id = identity.auth_provider_id
        user.auth_subject = identity.auth_subject
        user.metadata_json = {**user.metadata_json, **identity.metadata}

    session.commit()
    session.refresh(user)
    return user


def resolve_user_if_present(session: Session, request: Request) -> User | None:
    """Resolve a user when auth material is present, otherwise return None."""
    try:
        return resolve_or_create_user(session, request)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            return None
        raise


def _fallback_email_for_subject(subject: str) -> str:
    sanitized = subject.replace("|", ".").replace(":", ".").replace("/", ".")
    return f"{sanitized}@auth0.local"


def extract_bearer_token(request: Request) -> str | None:
    """Return the bearer token from the request if present."""
    authorization = request.headers.get("authorization", "")
    if not authorization.lower().startswith("bearer "):
        return None
    return authorization.split(" ", 1)[1].strip() or None
