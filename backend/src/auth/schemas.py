"""
Pydantic schemas for auth control plane identity responses.
"""
from pydantic import BaseModel, ConfigDict


class CurrentUserResponse(BaseModel):
    """Current authenticated user metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    display_name: str
    auth_subject: str | None
    auth_mode: str
    connected_account_count: int


class AuthConfigResponse(BaseModel):
    """Public auth bootstrap configuration for the frontend."""

    auth_mode: str
    allow_demo_mode: bool
    auth0_domain: str | None
    auth0_issuer: str | None
    auth0_client_id: str | None
    auth0_audience: str | None
    auth0_scope: str
    login_path: str
    callback_path: str


class AuthSessionResponse(BaseModel):
    """Current auth session state for login and app-shell boot."""

    authenticated: bool
    auth_mode: str
    allow_demo_mode: bool
    user: CurrentUserResponse | None = None
