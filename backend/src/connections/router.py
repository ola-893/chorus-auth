"""
Connected account API routes.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_user
from ..db import get_session
from ..db.enums import ProviderType
from ..db.models import User
from .schemas import (
    ConnectedAccountCreate,
    ConnectedAccountResponse,
    ConnectionCallbackResponse,
    ConnectionRefreshRequest,
    ConnectionStartRequest,
    ConnectionStartResponse,
)
from .service import (
    complete_connection,
    create_or_update_connection,
    disconnect_connection,
    list_connections,
    refresh_connection,
    start_connection,
)

router = APIRouter(prefix="/connections", tags=["connections"])


@router.get("", response_model=list[ConnectedAccountResponse])
def get_connections(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[ConnectedAccountResponse]:
    """List current-user connected accounts."""
    return list_connections(session, current_user)


@router.post("", response_model=ConnectedAccountResponse)
def post_connection(
    payload: ConnectedAccountCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ConnectedAccountResponse:
    """Create or update a connected account."""
    return create_or_update_connection(session, current_user, payload)


@router.post("/{provider}/start", response_model=ConnectionStartResponse)
def post_connection_start(
    provider: ProviderType,
    payload: ConnectionStartRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ConnectionStartResponse:
    """Start a Token Vault-backed provider connection flow."""
    return start_connection(session, current_user, provider, payload)


@router.get("/callback", response_model=ConnectionCallbackResponse)
def get_connection_callback(
    provider: ProviderType = Query(...),
    auth_session: str = Query(...),
    connect_code: str = Query(...),
    redirect_uri: str = Query(...),
    my_account_token: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ConnectionCallbackResponse:
    """Complete a provider callback after Auth0 redirects back."""
    return complete_connection(
        session,
        current_user,
        provider,
        auth_session=auth_session,
        connect_code=connect_code,
        redirect_uri=redirect_uri,
        my_account_token=my_account_token,
    )


@router.post("/{connection_id}/refresh", response_model=ConnectedAccountResponse)
def post_connection_refresh(
    connection_id: str,
    payload: ConnectionRefreshRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ConnectedAccountResponse:
    """Refresh a connection from the Token Vault source of truth."""
    return refresh_connection(session, current_user, connection_id, payload)


@router.delete("/{connection_id}", response_model=ConnectedAccountResponse)
def delete_connection(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ConnectedAccountResponse:
    """Disconnect a provider account without deleting activity history."""
    return disconnect_connection(session, current_user, connection_id)
