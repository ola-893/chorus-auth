"""
Database enums for the auth control plane.
"""
from enum import Enum


class ProviderType(str, Enum):
    GMAIL = "gmail"
    GITHUB = "github"


class AgentStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    QUARANTINED = "quarantined"


class ConnectedAccountStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class ConnectionHealthStatus(str, Enum):
    HEALTHY = "healthy"
    PENDING = "pending"
    DEGRADED = "degraded"
    ERROR = "error"


class ActionStatus(str, Enum):
    RECEIVED = "received"
    POLICY_BLOCKED = "policy_blocked"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    QUARANTINED = "quarantined"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"


class EnforcementDecision(str, Enum):
    ALLOW = "ALLOW"
    ALLOW_WITH_AUDIT = "ALLOW_WITH_AUDIT"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    BLOCK = "BLOCK"
    QUARANTINE = "QUARANTINE"
