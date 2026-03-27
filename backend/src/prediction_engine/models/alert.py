"""
Data models for alert classification and severity.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional

class AlertSeverity(str, Enum):
    """Severity levels for alerts."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class AlertContext:
    """Context information for classifying an alert."""
    incident_type: str
    affected_agents: List[str]
    resource_type: Optional[str] = None
    risk_score: float = 0.0
    active_quarantines: int = 0
    trust_score_trend: str = "stable"  # stable, degrading, improving
    timestamp: datetime = None

@dataclass
class ImpactAssessment:
    """Assessment of business and system impact."""
    system_impact_score: float  # 0.0 to 1.0
    business_impact_score: float  # 0.0 to 1.0
    estimated_downtime_minutes: int
    affected_services: List[str]
    description: str

@dataclass
class ClassifiedAlert:
    """Result of alert classification."""
    severity: AlertSeverity
    title: str
    description: str
    impact: ImpactAssessment
    recommended_action: str
    requires_voice_alert: bool
    context: AlertContext
    timestamp: datetime
