"""
Structured logging configuration for the Chorus Agent Conflict Predictor.
"""
import json
import logging
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional
try:
    from .config import settings
except ImportError:
    from config import settings


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs with consistent fields.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as structured JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON formatted log string
        """
        # Base log structure
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add agent_id if present in record
        if hasattr(record, 'agent_id'):
            log_entry["agent_id"] = record.agent_id
            
        # Add action_type if present in record
        if hasattr(record, 'action_type'):
            log_entry["action_type"] = record.action_type
            
        # Add context if present in record
        if hasattr(record, 'context'):
            log_entry["context"] = record.context
            
        # Add request_id if present in record
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = record.request_id
            
        # Add trust_score if present in record
        if hasattr(record, 'trust_score'):
            log_entry["trust_score"] = record.trust_score
            
        # Add risk_score if present in record
        if hasattr(record, 'risk_score'):
            log_entry["risk_score"] = record.risk_score
            
        # Add affected_agents if present in record
        if hasattr(record, 'affected_agents'):
            log_entry["affected_agents"] = record.affected_agents
            
        # Add exception information if present
        if record.exc_info and record.exc_info != (None, None, None) and not isinstance(record.exc_info, bool):
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }
            
        return json.dumps(log_entry, default=str)


class AgentLogger:
    """
    Enhanced logger with structured logging capabilities for agent interactions.
    """
    
    def __init__(self, name: str):
        """
        Initialize the agent logger.
        
        Args:
            name: Logger name
        """
        self.logger = logging.getLogger(name)
        
    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)
        
    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)
        
    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)
        
    def debug(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)
        
    def log_agent_action(
        self,
        level: str,
        message: str,
        agent_id: Optional[str] = None,
        action_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """
        Log an agent action with structured metadata.
        
        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            agent_id: ID of the agent performing the action
            action_type: Type of action being performed
            context: Additional context information
            **kwargs: Additional fields to include in log
        """
        log_level = getattr(logging, level.upper())
        
        # Create log record with extra fields
        extra = {}
        if agent_id:
            extra['agent_id'] = agent_id
        if action_type:
            extra['action_type'] = action_type
        if context:
            extra['context'] = context
            
        # Add any additional kwargs
        extra.update(kwargs)
        
        self.logger.log(log_level, message, extra=extra)
        
    def log_conflict_prediction(
        self,
        risk_score: float,
        affected_agents: list,
        prediction_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log conflict prediction with structured metadata.
        
        Args:
            risk_score: Calculated risk score
            affected_agents: List of affected agent IDs
            prediction_id: Unique prediction identifier
            context: Additional context information
        """
        extra = {
            'action_type': 'conflict_prediction',
            'risk_score': risk_score,
            'affected_agents': affected_agents,
        }
        
        if prediction_id:
            extra['request_id'] = prediction_id
        if context:
            extra['context'] = context
            
        level = "WARNING" if risk_score > settings.conflict_prediction.risk_threshold else "INFO"
        message = f"Conflict prediction: risk_score={risk_score:.3f}, affected_agents={len(affected_agents)}"
        
        self.logger.log(getattr(logging, level), message, extra=extra)
        
    def log_trust_score_update(
        self,
        agent_id: str,
        old_score: int,
        new_score: int,
        adjustment: int,
        reason: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log trust score updates with structured metadata.
        
        Args:
            agent_id: ID of the agent whose trust score changed
            old_score: Previous trust score
            new_score: New trust score
            adjustment: Score adjustment amount
            reason: Reason for the adjustment
            context: Additional context information
        """
        extra = {
            'agent_id': agent_id,
            'action_type': 'trust_score_update',
            'trust_score': new_score,
            'context': {
                'old_score': old_score,
                'adjustment': adjustment,
                'reason': reason,
                **(context or {})
            }
        }
        
        message = f"Trust score updated for agent {agent_id}: {old_score} -> {new_score} (adjustment: {adjustment}, reason: {reason})"
        self.logger.info(message, extra=extra)
        
    def log_quarantine_action(
        self,
        agent_id: str,
        action: str,
        reason: str,
        success: bool,
        trust_score: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log quarantine actions with structured metadata.
        
        Args:
            agent_id: ID of the agent being quarantined/released
            action: Action type (quarantine/release)
            reason: Reason for the action
            success: Whether the action was successful
            trust_score: Current trust score of the agent
            context: Additional context information
        """
        extra = {
            'agent_id': agent_id,
            'action_type': f'quarantine_{action}',
            'context': {
                'reason': reason,
                'success': success,
                **(context or {})
            }
        }
        
        if trust_score is not None:
            extra['trust_score'] = trust_score
            
        level = "INFO" if success else "ERROR"
        message = f"Quarantine {action} for agent {agent_id}: {'successful' if success else 'failed'} - {reason}"
        
        self.logger.log(getattr(logging, level), message, extra=extra)
        
    def log_system_error(
        self,
        error: Exception,
        component: str,
        operation: str,
        context: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None
    ) -> None:
        """
        Log system errors with structured metadata and stack traces.
        
        Args:
            error: Exception that occurred
            component: Component where error occurred
            operation: Operation being performed when error occurred
            context: Additional context information
            agent_id: Agent ID if error is agent-specific
        """
        extra = {
            'action_type': 'system_error',
            'context': {
                'component': component,
                'operation': operation,
                'error_type': type(error).__name__,
                **(context or {})
            }
        }
        
        if agent_id:
            extra['agent_id'] = agent_id
            
        message = f"System error in {component} during {operation}: {str(error)}"
        self.logger.error(message, extra=extra, exc_info=True)


class DatadogHandler(logging.Handler):
    """
    Custom logging handler that sends logs to Datadog.
    """
    def emit(self, record):
        # Avoid infinite loops
        if "datadog_client" in record.name or "datadog_api_client" in record.name:
            return

        try:
            # Lazy import to avoid circular dependency
            from .integrations.datadog_client import datadog_client
            
            if not datadog_client.enabled:
                return
            
            # Extract context
            context = getattr(record, 'context', {})
            if hasattr(record, 'agent_id'):
                context['agent_id'] = record.agent_id
            if hasattr(record, 'action_type'):
                context['action_type'] = record.action_type
                
            datadog_client.send_log(
                message=record.getMessage(),
                level=record.levelname,
                context=context,
                source=record.name
            )
        except Exception:
            self.handleError(record)


def setup_logging(
    level: Optional[str] = None,
    format_string: Optional[str] = None,
    use_structured: bool = True
) -> logging.Logger:
    """
    Set up logging configuration for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom log format string (ignored if use_structured=True)
        use_structured: Whether to use structured JSON logging
    
    Returns:
        Configured logger instance
    """
    log_level = level or settings.logging.level.value
    
    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create handler with appropriate formatter
    handler = logging.StreamHandler(sys.stdout)
    
    if use_structured:
        handler.setFormatter(StructuredFormatter())
    else:
        log_format = format_string or settings.logging.format
        handler.setFormatter(logging.Formatter(log_format))
    
    # Configure root logger
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(handler)
    
    # Add Datadog handler if enabled
    if settings.datadog.enabled:
        dd_handler = DatadogHandler()
        # Set level to at least INFO for Datadog to avoid noise
        dd_handler.setLevel(logging.INFO) 
        root_logger.addHandler(dd_handler)
    
    # Create application logger
    logger = logging.getLogger("chorus.agent_conflict_predictor")
    
    # Set specific log levels for external libraries
    logging.getLogger("google.genai").setLevel(logging.WARNING)
    logging.getLogger("confluent_kafka").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)
    logging.getLogger("datadog").setLevel(logging.WARNING)
    
    return logger


def get_agent_logger(name: str) -> AgentLogger:
    """
    Get an enhanced agent logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        AgentLogger instance
    """
    return AgentLogger(name)


# Global logger instances
logger = setup_logging()
agent_logger = get_agent_logger("chorus.agent_conflict_predictor")