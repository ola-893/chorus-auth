"""
Connected account persistence and vault lookup helpers.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..control_plane_config import settings
from ..db.models import ConnectedAccount, User
from ..realtime.events import publish_dashboard_event
from ..vault.adapters import get_vault_adapter
from .schemas import ConnectedAccountCreate, ConnectedAccountResponse


def serialize_connected_account(user: User, account: ConnectedAccount) -> ConnectedAccountResponse:
    """Convert an account record into an API response."""
    vault = get_vault_adapter()
    access = vault.get_provider_access(user, account.provider, account.scopes_json)
    return ConnectedAccountResponse(
        id=account.id,
        provider=account.provider,
        external_account_id=account.external_account_id,
        scopes=list(account.scopes_json),
        status=account.status,
        connection_mode=account.connection_mode,
        vault_reference=access.reference,
    )


def list_connections(session: Session, user: User) -> list[ConnectedAccountResponse]:
    """Return all connections for the user."""
    accounts = session.scalars(
        select(ConnectedAccount)
        .where(ConnectedAccount.user_id == user.id)
        .order_by(ConnectedAccount.created_at.asc())
    ).all()
    return [serialize_connected_account(user, account) for account in accounts]


def create_or_update_connection(
    session: Session,
    user: User,
    payload: ConnectedAccountCreate,
) -> ConnectedAccountResponse:
    """Create or update a connected account for the user."""
    account = session.scalar(
        select(ConnectedAccount).where(
            ConnectedAccount.user_id == user.id,
            ConnectedAccount.provider == payload.provider,
        )
    )

    if account is None:
        account = ConnectedAccount(
            user_id=user.id,
            provider=payload.provider,
            external_account_id=payload.external_account_id,
            scopes_json=payload.scopes,
            status=payload.status,
            connection_mode=settings.vault_mode,
            metadata_json=payload.metadata,
        )
        session.add(account)
    else:
        account.external_account_id = payload.external_account_id
        account.scopes_json = payload.scopes
        account.status = payload.status
        account.connection_mode = settings.vault_mode
        account.metadata_json = payload.metadata

    session.commit()
    session.refresh(account)
    response = serialize_connected_account(user, account)
    publish_dashboard_event("connection.updated", response.model_dump(mode="json"))
    return response
