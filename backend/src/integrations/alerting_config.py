"""
Configuration for Datadog alerting system.
"""
from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum

class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class NotificationChannel(str, Enum):
    """Available notification channels."""
    SLACK_OPS = "slack-ops"
    SLACK_CRITICAL = "slack-critical"
    PAGERDUTY = "pagerduty"
    PAGERDUTY_ESCALATION = "pagerduty-escalation"
    INCIDENT_COMMANDER = "incident-commander"
    ON_CALL_ENGINEER = "on-call-engineer"

@dataclass
class AlertThresholds:
    """Alert threshold configuration."""
    warning: float
    critical: float
    emergency: float = None

@dataclass
class EscalationRule:
    """Alert escalation rule configuration."""
    initial_notification: List[NotificationChannel]
    escalation_time: int  # minutes
    escalation_notification: List[NotificationChannel]

class AlertingConfig:
    """Central configuration for the alerting system."""
    
    # Trust score thresholds
    TRUST_SCORE_THRESHOLDS = AlertThresholds(
        warning=30.0,
        critical=20.0,
        emergency=10.0
    )
    
    # Quarantine thresholds
    QUARANTINE_THRESHOLDS = AlertThresholds(
        warning=2,
        critical=3,
        emergency=5
    )
    
    # Conflict rate thresholds
    CONFLICT_RATE_THRESHOLDS = AlertThresholds(
        warning=0.7,
        critical=1.0,
        emergency=1.5
    )
    
    # Notification channel mappings
    NOTIFICATION_CHANNELS = {
        NotificationChannel.SLACK_OPS: "@slack-ops",
        NotificationChannel.SLACK_CRITICAL: "@slack-critical",
        NotificationChannel.PAGERDUTY: "@pagerduty",
        NotificationChannel.PAGERDUTY_ESCALATION: "@pagerduty-escalation",
        NotificationChannel.INCIDENT_COMMANDER: "@incident-commander",
        NotificationChannel.ON_CALL_ENGINEER: "@on-call-engineer"
    }
    
    # Escalation rules
    ESCALATION_RULES = {
        "trust_score_critical": EscalationRule(
            initial_notification=[NotificationChannel.PAGERDUTY, NotificationChannel.SLACK_CRITICAL],
            escalation_time=30,
            escalation_notification=[NotificationChannel.PAGERDUTY_ESCALATION, NotificationChannel.ON_CALL_ENGINEER]
        ),
        "multiple_quarantines": EscalationRule(
            initial_notification=[NotificationChannel.PAGERDUTY, NotificationChannel.SLACK_CRITICAL],
            escalation_time=15,
            escalation_notification=[NotificationChannel.INCIDENT_COMMANDER, NotificationChannel.PAGERDUTY_ESCALATION]
        ),
        "system_health_critical": EscalationRule(
            initial_notification=[NotificationChannel.SLACK_OPS],
            escalation_time=60,
            escalation_notification=[NotificationChannel.PAGERDUTY]
        ),
        "conflict_rate_critical": EscalationRule(
            initial_notification=[NotificationChannel.SLACK_CRITICAL],
            escalation_time=45,
            escalation_notification=[NotificationChannel.PAGERDUTY, NotificationChannel.INCIDENT_COMMANDER]
        )
    }
    
    # Auto-resolution configuration
    AUTO_RESOLUTION_CONFIG = {
        "enabled": True,
        "check_interval": 60,  # seconds
        "conditions": {
            "trust_score_recovery": {
                "condition": "trust_score > warning_threshold + 5",
                "description": "Trust score recovered 5 points above warning threshold"
            },
            "quarantine_recovery": {
                "condition": "quarantined_count == 0",
                "description": "All agents released from quarantine"
            },
            "system_health_recovery": {
                "condition": "all_components_healthy",
                "description": "All system components reporting healthy status"
            },
            "conflict_rate_recovery": {
                "condition": "conflict_rate < warning_threshold - 0.1",
                "description": "Conflict rate dropped below warning threshold with buffer"
            }
        },
        "recovery_notification": True,
        "recovery_delay": 300  # seconds - wait before confirming recovery
    }
    
    # Alert message templates
    ALERT_TEMPLATES = {
        "trust_score_warning": {
            "title": "[Chorus] Agent Trust Score Low - Warning",
            "message": "Agent trust score dropped below {threshold}. Agent: {agent_id}. Current score: {value}. Investigation recommended.",
            "tags": ["service:chorus", "alert_type:trust_score", "severity:warning"]
        },
        "trust_score_critical": {
            "title": "[Chorus] Agent Trust Score Critical",
            "message": "CRITICAL: Agent trust score dropped below {threshold}. Agent: {agent_id}. Current score: {value}. Immediate quarantine recommended.",
            "tags": ["service:chorus", "alert_type:trust_score", "severity:critical"]
        },
        "multiple_quarantines": {
            "title": "[Chorus] Multiple Agents Quarantined",
            "message": "CRITICAL: {count} agents quarantined in the last {timeframe} minutes. Possible cascade failure detected.",
            "tags": ["service:chorus", "alert_type:quarantine", "severity:critical"]
        },
        "system_health_degraded": {
            "title": "[Chorus] System Health Degradation",
            "message": "System component unhealthy. Component: {component}. Status: {status}. Impact: {impact}.",
            "tags": ["service:chorus", "alert_type:system_health"]
        },
        "conflict_rate_high": {
            "title": "[Chorus] High Conflict Prediction Rate",
            "message": "Conflict prediction rate exceeds normal thresholds. Rate: {rate}. Possible system stress detected.",
            "tags": ["service:chorus", "alert_type:conflict_rate", "severity:warning"]
        },
        "conflict_rate_critical": {
            "title": "[Chorus] Critical Conflict Prediction Rate",
            "message": "CRITICAL: Conflict prediction rate severely elevated. Rate: {rate}. System under extreme stress.",
            "tags": ["service:chorus", "alert_type:conflict_rate", "severity:critical"]
        },
        "circuit_breaker_open": {
            "title": "[Chorus] Circuit Breaker Activation",
            "message": "Circuit breaker activated for {service}. Degraded functionality expected. Reason: {reason}.",
            "tags": ["service:chorus", "alert_type:circuit_breaker"]
        },
        "alert_resolved": {
            "title": "[Chorus] Alert Resolution",
            "message": "Alert automatically resolved. Type: {alert_type}. Recovery confirmed. System health restored.",
            "tags": ["service:chorus", "alert_type:resolution", "severity:info"]
        }
    }
    
    # Monitor query templates
    MONITOR_QUERIES = {
        "trust_score_warning": "avg(last_5m):avg:chorus.agent.trust_score{{*}} < {threshold}",
        "trust_score_critical": "avg(last_5m):avg:chorus.agent.trust_score{{*}} < {threshold}",
        "multiple_quarantines": "sum(last_10m):sum:chorus.agent.quarantined{{*}} > {threshold}",
        "system_health_redis": "\"chorus.system.health.redis\".over(\"env:production\").last(2).count_by_status()",
        "system_health_datadog": "\"chorus.system.health.datadog\".over(\"env:production\").last(2).count_by_status()",
        "system_health_gemini": "\"chorus.system.health.gemini\".over(\"env:production\").last(2).count_by_status()",
        "conflict_rate_warning": "avg(last_15m):avg:chorus.conflict.rate{{*}} > {threshold}",
        "conflict_rate_critical": "avg(last_15m):avg:chorus.conflict.rate{{*}} > {threshold}",
        "circuit_breaker_open": "sum(last_5m):sum:chorus.circuit_breaker.open{{*}} > 0"
    }
    
    @classmethod
    def get_threshold_for_alert_type(cls, alert_type: str, severity: AlertSeverity) -> float:
        """Get threshold value for a specific alert type and severity."""
        if alert_type == "trust_score":
            thresholds = cls.TRUST_SCORE_THRESHOLDS
        elif alert_type == "quarantine":
            thresholds = cls.QUARANTINE_THRESHOLDS
        elif alert_type == "conflict_rate":
            thresholds = cls.CONFLICT_RATE_THRESHOLDS
        else:
            raise ValueError(f"Unknown alert type: {alert_type}")
        
        if severity == AlertSeverity.WARNING:
            return thresholds.warning
        elif severity == AlertSeverity.CRITICAL:
            return thresholds.critical
        else:
            raise ValueError(f"Unknown severity: {severity}")
    
    @classmethod
    def get_notification_channels(cls, escalation_rule: str) -> List[str]:
        """Get notification channels for an escalation rule."""
        rule = cls.ESCALATION_RULES.get(escalation_rule)
        if not rule:
            return []
        
        channels = []
        for channel in rule.initial_notification:
            channels.append(cls.NOTIFICATION_CHANNELS[channel])
        
        return channels
    
    @classmethod
    def get_escalation_channels(cls, escalation_rule: str) -> List[str]:
        """Get escalation notification channels for an escalation rule."""
        rule = cls.ESCALATION_RULES.get(escalation_rule)
        if not rule:
            return []
        
        channels = []
        for channel in rule.escalation_notification:
            channels.append(cls.NOTIFICATION_CHANNELS[channel])
        
        return channels
    
    @classmethod
    def format_alert_message(cls, alert_type: str, **kwargs) -> Dict[str, Any]:
        """Format an alert message using the template."""
        template = cls.ALERT_TEMPLATES.get(alert_type)
        if not template:
            raise ValueError(f"Unknown alert type: {alert_type}")
        
        return {
            "title": template["title"].format(**kwargs),
            "message": template["message"].format(**kwargs),
            "tags": template["tags"]
        }
    
    @classmethod
    def get_monitor_query(cls, query_type: str, **kwargs) -> str:
        """Get a formatted monitor query."""
        template = cls.MONITOR_QUERIES.get(query_type)
        if not template:
            raise ValueError(f"Unknown query type: {query_type}")
        
        return template.format(**kwargs)