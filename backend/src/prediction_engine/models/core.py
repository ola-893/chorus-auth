"""
Core data models for the agent conflict predictor.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum


class MessageType(Enum):
    """Types of messages agents can send."""
    RESOURCE_REQUEST = "resource_request"
    RESOURCE_RESPONSE = "resource_response"
    STATUS_UPDATE = "status_update"
    HEARTBEAT = "heartbeat"


class ResourceType(Enum):
    """Types of resources agents can request."""
    CPU = "cpu"
    MEMORY = "memory"
    NETWORK = "network"
    STORAGE = "storage"
    DATABASE = "database"


@dataclass
class AgentIntention:
    """Represents an agent's intention to perform an action."""
    agent_id: str
    resource_type: str
    requested_amount: int
    priority_level: int
    timestamp: datetime


@dataclass
class AgentMessage:
    """Message sent between agents."""
    sender_id: str
    receiver_id: str
    message_type: str
    content: Dict[str, Any]
    timestamp: datetime


@dataclass
class ResourceRequest:
    """Request for a shared resource."""
    agent_id: str
    resource_type: str
    amount: int
    priority: int
    timestamp: datetime


@dataclass
class ConflictAnalysis:
    """Result of conflict analysis from Gemini API."""
    risk_score: float
    confidence_level: float
    affected_agents: List[str]
    predicted_failure_mode: str
    nash_equilibrium: Optional[Dict[str, Any]]
    timestamp: datetime


@dataclass
class QuarantineAction:
    """Record of a quarantine action taken."""
    agent_id: str
    reason: str
    timestamp: datetime
    duration: Optional[int]
    trust_score_before: int
    trust_score_after: int


@dataclass
class TrustScoreEntry:
    """Trust score record for an agent."""
    agent_id: str
    current_score: int  # 0-100
    last_updated: datetime
    adjustment_history: List[Dict[str, Any]]
    quarantine_count: int
    creation_time: datetime


@dataclass
class GameState:
    """Represents the current state for game theory analysis."""
    agents: List[str]
    resources: Dict[str, int]
    intentions: List[AgentIntention]
    timestamp: datetime


@dataclass
class EquilibriumSolution:
    """Nash equilibrium solution from game theory analysis."""
    strategy_profile: Dict[str, str]
    payoffs: Dict[str, float]
    stability_score: float
    timestamp: datetime
    equilibrium_type: Optional[str] = None


@dataclass
class InterventionAction:
    """Action recommended by the intervention engine."""
    action_type: str
    target_agent: str
    reason: str
    confidence: float
    timestamp: datetime


@dataclass
class ResourceStatus:
    """Current status of a shared resource."""
    resource_type: str
    total_capacity: int
    current_usage: int
    pending_requests: int
    timestamp: datetime


@dataclass
class ContentionEvent:
    """Event representing resource contention."""
    resource_type: str
    competing_agents: List[str]
    severity: float
    timestamp: datetime


@dataclass
class RequestResult:
    """Result of processing a resource request."""
    success: bool
    allocated_amount: int
    reason: str
    timestamp: datetime


@dataclass
class QuarantineResult:
    """Result of a quarantine operation."""
    success: bool
    agent_id: str
    reason: str
    timestamp: datetime