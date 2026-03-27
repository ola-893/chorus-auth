"""
Connected account persistence and vault lookup helpers.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..control_plane_config import settings
from ..db.models import ConnectedAccount, User
from ..vault.adapters import get_vault_adapter
from .schemas import ConnectedAccountCreate, ConnectedAccountResponse


def list_connections(session: Session, user: User) -> list[ConnectedAccountResponse]:
    """Return all connections for the user."""
    vault = get_vault_adapter()
    accounts = session.scalars(
        select(ConnectedAccount)
        .where(ConnectedAccount.user_id == user.id)
        .order_by(ConnectedAccount.created_at.asc())
    ).all()

    results: list[ConnectedAccountResponse] = []
    for account in accounts:
        access = vault.get_provider_access(user, account.provider, account.scopes_json)
        results.append(
            ConnectedAccountResponse(
                id=account.id,
                provider=account.provider,
                external_account_id=account.external_account_id,
                scopes=list(account.scopes_json),
                status=account.status,
                connection_mode=account.connection_mode,
                vault_reference=access.reference,
            )
        )
    return results


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
    return list_connections(session, user)[-1]
