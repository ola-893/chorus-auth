"""
ORM models for the auth control plane.
"""
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, PrimaryKeyMixin, TimestampMixin, utc_now
from .enums import (
    ActionStatus,
    AgentStatus,
    ApprovalStatus,
    ConnectedAccountStatus,
    EnforcementDecision,
    ExecutionStatus,
    ProviderType,
    RiskLevel,
)


class User(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_provider_id: Mapped[Optional[str]] = mapped_column(String(255))
    auth_subject: Mapped[Optional[str]] = mapped_column(String(255))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    agents: Mapped[list["Agent"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    connected_accounts: Mapped[list["ConnectedAccount"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    action_requests: Mapped[list["ActionRequest"]] = relationship(back_populates="owner")
    audit_events: Mapped[list["AuditEvent"]] = relationship(back_populates="user")


class Agent(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agents"

    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[AgentStatus] = mapped_column(Enum(AgentStatus), default=AgentStatus.ACTIVE, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    last_violation_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    quarantined_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    owner: Mapped["User"] = relationship(back_populates="agents")
    capability_grants: Mapped[list["AgentCapabilityGrant"]] = relationship(back_populates="agent", cascade="all, delete-orphan")
    action_requests: Mapped[list["ActionRequest"]] = relationship(back_populates="agent")
    quarantine_records: Mapped[list["QuarantineRecord"]] = relationship(back_populates="agent", cascade="all, delete-orphan")
    audit_events: Mapped[list["AuditEvent"]] = relationship(back_populates="agent")


class ConnectedAccount(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "connected_accounts"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_connected_accounts_user_provider"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    provider: Mapped[ProviderType] = mapped_column(Enum(ProviderType), nullable=False)
    external_account_id: Mapped[Optional[str]] = mapped_column(String(255))
    scopes_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[ConnectedAccountStatus] = mapped_column(
        Enum(ConnectedAccountStatus),
        default=ConnectedAccountStatus.CONNECTED,
        nullable=False,
    )
    connection_mode: Mapped[str] = mapped_column(String(50), default="mock", nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    owner: Mapped["User"] = relationship(back_populates="connected_accounts")
    action_requests: Mapped[list["ActionRequest"]] = relationship(back_populates="connected_account")


class Capability(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "capabilities"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    provider: Mapped[ProviderType] = mapped_column(Enum(ProviderType), nullable=False)
    action_type: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    risk_level_default: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel),
        default=RiskLevel.LOW,
        nullable=False,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    grants: Mapped[list["AgentCapabilityGrant"]] = relationship(back_populates="capability")


class AgentCapabilityGrant(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_capability_grants"
    __table_args__ = (
        UniqueConstraint("agent_id", "capability_id", name="uq_agent_capability_grants_agent_capability"),
    )

    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), nullable=False, index=True)
    capability_id: Mapped[str] = mapped_column(ForeignKey("capabilities.id"), nullable=False, index=True)
    created_by_user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"))
    constraints_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    agent: Mapped["Agent"] = relationship(back_populates="capability_grants")
    capability: Mapped["Capability"] = relationship(back_populates="grants")


class ActionRequest(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "action_requests"
    __table_args__ = (
        Index("ix_action_requests_status_requested_at", "status", "requested_at"),
    )

    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), nullable=False, index=True)
    connected_account_id: Mapped[Optional[str]] = mapped_column(ForeignKey("connected_accounts.id"))
    provider: Mapped[ProviderType] = mapped_column(Enum(ProviderType), nullable=False)
    capability_name: Mapped[str] = mapped_column(String(255), nullable=False)
    action_type: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[ActionStatus] = mapped_column(Enum(ActionStatus), default=ActionStatus.RECEIVED, nullable=False)
    enforcement_decision: Mapped[Optional[EnforcementDecision]] = mapped_column(Enum(EnforcementDecision))
    explanation: Mapped[Optional[str]] = mapped_column(Text)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    owner: Mapped["User"] = relationship(back_populates="action_requests")
    agent: Mapped["Agent"] = relationship(back_populates="action_requests")
    connected_account: Mapped[Optional["ConnectedAccount"]] = relationship(back_populates="action_requests")
    risk_assessment: Mapped[Optional["RiskAssessment"]] = relationship(back_populates="action_request", uselist=False, cascade="all, delete-orphan")
    approval_decision: Mapped[Optional["ApprovalDecision"]] = relationship(back_populates="action_request", uselist=False, cascade="all, delete-orphan")
    execution_record: Mapped[Optional["ExecutionRecord"]] = relationship(back_populates="action_request", uselist=False, cascade="all, delete-orphan")
    audit_events: Mapped[list["AuditEvent"]] = relationship(back_populates="action_request", cascade="all, delete-orphan")


class RiskAssessment(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "risk_assessments"
    __table_args__ = (
        UniqueConstraint("action_request_id", name="uq_risk_assessments_action_request"),
    )

    action_request_id: Mapped[str] = mapped_column(ForeignKey("action_requests.id"), nullable=False, index=True)
    score: Mapped[Optional[float]] = mapped_column(Float)
    level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel), nullable=False)
    source: Mapped[str] = mapped_column(String(100), default="rules", nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[EnforcementDecision] = mapped_column(Enum(EnforcementDecision), nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float)
    assessment_metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    action_request: Mapped["ActionRequest"] = relationship(back_populates="risk_assessment")


class ApprovalDecision(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "approval_decisions"
    __table_args__ = (
        UniqueConstraint("action_request_id", name="uq_approval_decisions_action_request"),
    )

    action_request_id: Mapped[str] = mapped_column(ForeignKey("action_requests.id"), nullable=False, index=True)
    status: Mapped[ApprovalStatus] = mapped_column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING, nullable=False)
    approver_user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[Optional[str]] = mapped_column(Text)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    action_request: Mapped["ActionRequest"] = relationship(back_populates="approval_decision")


class ExecutionRecord(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "execution_records"
    __table_args__ = (
        UniqueConstraint("action_request_id", name="uq_execution_records_action_request"),
    )

    action_request_id: Mapped[str] = mapped_column(ForeignKey("action_requests.id"), nullable=False, index=True)
    status: Mapped[ExecutionStatus] = mapped_column(Enum(ExecutionStatus), default=ExecutionStatus.PENDING, nullable=False)
    provider_response_summary: Mapped[Optional[str]] = mapped_column(Text)
    external_reference_id: Mapped[Optional[str]] = mapped_column(String(255))
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    action_request: Mapped["ActionRequest"] = relationship(back_populates="execution_record")


class QuarantineRecord(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "quarantine_records"
    __table_args__ = (
        Index("ix_quarantine_records_agent_active", "agent_id", "active"),
    )

    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), nullable=False, index=True)
    trigger_action_request_id: Mapped[Optional[str]] = mapped_column(ForeignKey("action_requests.id"))
    trigger_reason: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    agent: Mapped["Agent"] = relationship(back_populates="quarantine_records")


class AuditEvent(PrimaryKeyMixin, Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_occurred_at", "occurred_at"),
    )

    action_request_id: Mapped[Optional[str]] = mapped_column(ForeignKey("action_requests.id"), index=True)
    agent_id: Mapped[Optional[str]] = mapped_column(ForeignKey("agents.id"), index=True)
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    action_request: Mapped[Optional["ActionRequest"]] = relationship(back_populates="audit_events")
    agent: Mapped[Optional["Agent"]] = relationship(back_populates="audit_events")
    user: Mapped[Optional["User"]] = relationship(back_populates="audit_events")
