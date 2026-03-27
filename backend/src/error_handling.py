"""
Centralized error handling and resilience system for the Chorus Agent Conflict Predictor.
"""
import functools
import time
from typing import Any, Callable, Dict, Optional, Type, Union
from contextlib import contextmanager
import google.genai as genai
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
from .logging_config import get_agent_logger

agent_logger = get_agent_logger(__name__)


class ChorusError(Exception):
    """Base exception class for Chorus system errors."""
    
    def __init__(self, message: str, component: str, operation: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.component = component
        self.operation = operation
        self.context = context or {}


class GeminiAPIError(ChorusError):
    """Exception for Gemini API related errors."""
    pass


class RedisOperationError(ChorusError):
    """Exception for Redis operation errors."""
    pass


class AgentSimulationError(ChorusError):
    """Exception for agent simulation errors."""
    pass


class SystemRecoveryError(ChorusError):
    """Exception for system recovery failures."""
    pass


def retry_with_exponential_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_multiplier: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying operations with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_multiplier: Multiplier for exponential backoff
        exceptions: Tuple of exception types to retry on
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        agent_logger.log_system_error(
                            e,
                            component="retry_handler",
                            operation=func.__name__,
                            context={
                                "max_retries": max_retries,
                                "final_attempt": True
                            }
                        )
                        raise
                    
                    delay = min(base_delay * (backoff_multiplier ** attempt), max_delay)
                    
                    agent_logger.log_agent_action(
                        "WARNING",
                        f"Operation failed, retrying in {delay:.2f}s",
                        action_type="retry_attempt",
                        context={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "max_retries": max_retries,
                            "delay": delay,
                            "error": str(e)
                        }
                    )
                    
                    time.sleep(delay)
            
            # This should never be reached, but just in case
            raise last_exception
        
        return wrapper
    return decorator


def handle_gemini_api_errors(func: Callable) -> Callable:
    """
    Decorator for handling Gemini API specific errors.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (genai.errors.APIError, genai.errors.ClientError, genai.errors.ServerError) as e:
            error_context = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "function": func.__name__
            }
            
            agent_logger.log_system_error(
                e,
                component="gemini_api",
                operation=func.__name__,
                context=error_context
            )
            
            raise GeminiAPIError(
                f"Gemini API error in {func.__name__}: {str(e)}",
                component="gemini_api",
                operation=func.__name__,
                context=error_context
            ) from e
        except Exception as e:
            agent_logger.log_system_error(
                e,
                component="gemini_api",
                operation=func.__name__,
                context={"unexpected_error": True}
            )
            raise
    
    return wrapper


def handle_redis_errors(func: Callable) -> Callable:
    """
    Decorator for handling Redis specific errors.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (RedisError, RedisConnectionError) as e:
            error_context = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "function": func.__name__
            }
            
            agent_logger.log_system_error(
                e,
                component="redis",
                operation=func.__name__,
                context=error_context
            )
            
            raise RedisOperationError(
                f"Redis error in {func.__name__}: {str(e)}",
                component="redis",
                operation=func.__name__,
                context=error_context
            ) from e
        except Exception as e:
            agent_logger.log_system_error(
                e,
                component="redis",
                operation=func.__name__,
                context={"unexpected_error": True}
            )
            raise
    
    return wrapper


def isolate_agent_errors(func: Callable) -> Callable:
    """
    Decorator for isolating agent simulation errors to prevent cascade failures.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Extract agent_id if available
            agent_id = None
            if args and hasattr(args[0], 'agent_id'):
                agent_id = args[0].agent_id
            elif 'agent_id' in kwargs:
                agent_id = kwargs['agent_id']
            
            error_context = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "function": func.__name__,
                "isolated": True
            }
            
            agent_logger.log_system_error(
                e,
                component="agent_simulation",
                operation=func.__name__,
                agent_id=agent_id,
                context=error_context
            )
            
            # Return a safe default or None to prevent cascade failures
            return None
    
    return wrapper


@contextmanager
def system_recovery_context(component: str, operation: str, fallback_action: Optional[Callable] = None):
    """
    Context manager for system recovery and graceful degradation.
    
    Args:
        component: Component name where operation is being performed
        operation: Operation being performed
        fallback_action: Optional fallback action to execute on error
    """
    try:
        yield
    except Exception as e:
        agent_logger.log_system_error(
            e,
            component=component,
            operation=operation,
            context={"recovery_attempted": True}
        )
        
        if fallback_action:
            try:
                agent_logger.log_agent_action(
                    "INFO",
                    f"Executing fallback action for {component}.{operation}",
                    action_type="fallback_execution",
                    context={"component": component, "operation": operation}
                )
                fallback_action()
            except Exception as fallback_error:
                agent_logger.log_system_error(
                    fallback_error,
                    component=component,
                    operation=f"{operation}_fallback",
                    context={"fallback_failed": True}
                )
                raise SystemRecoveryError(
                    f"Both primary operation and fallback failed in {component}.{operation}",
                    component=component,
                    operation=operation,
                    context={"primary_error": str(e), "fallback_error": str(fallback_error)}
                ) from e
        else:
            # Re-raise the original exception if no fallback is provided
            raise


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for preventing cascade failures.
    """
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0, expected_exception: Type[Exception] = Exception, service_name: str = "unknown", on_state_change: Optional[Callable[[str], None]] = None):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before attempting recovery
            expected_exception: Exception type to monitor
            service_name: Name of the service being protected
            on_state_change: Optional callback function to be called on state change
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.service_name = service_name
        self.on_state_change = on_state_change
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self._set_state("HALF_OPEN")
                    agent_logger.log_agent_action(
                        "INFO",
                        f"Circuit breaker attempting recovery for {func.__name__}",
                        action_type="circuit_breaker_recovery",
                        context={"function": func.__name__}
                    )
                else:
                    agent_logger.log_agent_action(
                        "WARNING",
                        f"Circuit breaker is OPEN for {func.__name__}",
                        action_type="circuit_breaker_blocked",
                        context={"function": func.__name__}
                    )
                    raise SystemRecoveryError(
                        f"Circuit breaker is OPEN for {func.__name__}",
                        component="circuit_breaker",
                        operation=func.__name__,
                        context={"state": self.state, "failure_count": self.failure_count}
                    )
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise
        
        return wrapper

    def _set_state(self, new_state: str) -> None:
        if self.state != new_state:
            old_state = self.state
            self.state = new_state
            self._emit_state_change_event(old_state, new_state)
            if self.on_state_change:
                self.on_state_change(new_state)
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _on_success(self) -> None:
        """Handle successful operation."""
        if self.state == "HALF_OPEN":
            self._set_state("CLOSED")
            self.failure_count = 0
            agent_logger.log_agent_action(
                "INFO",
                "Circuit breaker recovered successfully",
                action_type="circuit_breaker_recovered"
            )
    
    def _on_failure(self) -> None:
        """Handle failed operation."""
        old_state = self.state
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self._set_state("OPEN")
            agent_logger.log_agent_action(
                "ERROR",
                f"Circuit breaker opened due to {self.failure_count} failures",
                action_type="circuit_breaker_opened",
                context={"failure_count": self.failure_count, "threshold": self.failure_threshold}
            )
    
    def _emit_state_change_event(self, old_state: str, new_state: str) -> None:
        """
        Emit circuit breaker state change event.
        
        Args:
            old_state: Previous circuit breaker state
            new_state: New circuit breaker state
        """
        try:
            from .event_bus import event_bus
            event_bus.publish("circuit_breaker_state_change", {
                "service": self.service_name,
                "old_state": old_state,
                "new_state": new_state,
                "failure_count": self.failure_count,
                "timestamp": time.time()
            })
        except Exception as e:
            # Don't fail circuit breaker operation if event emission fails
            agent_logger.log_system_error(
                e,
                component="circuit_breaker",
                operation="emit_state_change_event",
                context={"service": self.service_name}
            )


# Pre-configured circuit breakers for common operations
gemini_circuit_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=30.0,
    expected_exception=GeminiAPIError,
    service_name="gemini_api"
)

redis_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=10.0,
    expected_exception=RedisOperationError,
    service_name="redis"
)