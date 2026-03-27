"""
Audit event helpers for the auth control plane.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import ActionRequest, Agent, AuditEvent, User
from .schemas import AuditEventResponse


def append_audit_event(
    session: Session,
    event_type: str,
    message: str,
    *,
    action_request: ActionRequest | None = None,
    agent: Agent | None = None,
    user: User | None = None,
    details: dict | None = None,
) -> AuditEvent:
    """Persist an audit event."""
    event = AuditEvent(
        action_request_id=action_request.id if action_request else None,
        agent_id=agent.id if agent else None,
        user_id=user.id if user else None,
        event_type=event_type,
        message=message,
        details_json=details or {},
    )
    session.add(event)
    session.flush()
    return event


def serialize_audit_event(event: AuditEvent) -> AuditEventResponse:
    """Convert an ORM audit event to an API response."""
    return AuditEventResponse(
        id=event.id,
        action_request_id=event.action_request_id,
        agent_id=event.agent_id,
        user_id=event.user_id,
        event_type=event.event_type,
        message=event.message,
        details=event.details_json,
        occurred_at=event.occurred_at,
    )


def list_audit_events(session: Session, user: User) -> list[AuditEventResponse]:
    """Return audit events for the current user."""
    events = session.scalars(
        select(AuditEvent)
        .where(AuditEvent.user_id == user.id)
        .order_by(AuditEvent.occurred_at.desc())
    ).all()
    return [serialize_audit_event(event) for event in events]


def list_audit_events_for_action(session: Session, user: User, action_id: str) -> list[AuditEventResponse]:
    """Return audit events for a specific action."""
    events = session.scalars(
        select(AuditEvent)
        .where(
            AuditEvent.user_id == user.id,
            AuditEvent.action_request_id == action_id,
        )
        .order_by(AuditEvent.occurred_at.asc())
    ).all()
    return [serialize_audit_event(event) for event in events]
