"""
Auth API routes for resolving the current user.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..control_plane_config import settings
from ..db import get_session
from ..db.models import ConnectedAccount
from .dependencies import get_current_user, get_optional_current_user
from .schemas import AuthConfigResponse, AuthSessionResponse, CurrentUserResponse

router = APIRouter(tags=["auth"])


@router.get("/me", response_model=CurrentUserResponse)
def get_me(
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CurrentUserResponse:
    """Return the current authenticated user."""
    connection_count = session.scalar(
        select(func.count(ConnectedAccount.id)).where(ConnectedAccount.user_id == current_user.id)
    )

    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        auth_subject=current_user.auth_subject,
        auth_mode=settings.auth_mode,
        connected_account_count=int(connection_count or 0),
    )


@router.get("/auth/config", response_model=AuthConfigResponse)
def get_auth_config() -> AuthConfigResponse:
    """Return non-sensitive frontend auth bootstrap configuration."""
    issuer = settings.auth0_issuer
    if not issuer and settings.auth0_domain:
        domain = settings.auth0_domain.rstrip("/")
        if not domain.startswith("http"):
            domain = f"https://{domain}"
        issuer = f"{domain}/"

    return AuthConfigResponse(
        auth_mode=settings.auth_mode,
        allow_demo_mode=settings.allow_demo_mode,
        auth0_domain=settings.auth0_domain,
        auth0_issuer=issuer,
        auth0_client_id=settings.auth0_client_id,
        auth0_audience=settings.auth0_audience,
        auth0_scope=settings.auth0_scope,
        login_path="/login",
        callback_path="/login/callback",
    )


@router.get("/auth/session", response_model=AuthSessionResponse)
def get_auth_session(
    current_user=Depends(get_optional_current_user),
    session: Session = Depends(get_session),
) -> AuthSessionResponse:
    """Return a clean signed-in or signed-out session state."""
    if current_user is None:
        return AuthSessionResponse(
            authenticated=False,
            auth_mode=settings.auth_mode,
            allow_demo_mode=settings.allow_demo_mode,
            user=None,
        )

    connection_count = session.scalar(
        select(func.count(ConnectedAccount.id)).where(ConnectedAccount.user_id == current_user.id)
    )
    return AuthSessionResponse(
        authenticated=True,
        auth_mode=settings.auth_mode,
        allow_demo_mode=settings.allow_demo_mode,
        user=CurrentUserResponse(
            id=current_user.id,
            email=current_user.email,
            display_name=current_user.display_name,
            auth_subject=current_user.auth_subject,
            auth_mode=settings.auth_mode,
            connected_account_count=int(connection_count or 0),
        ),
    )
