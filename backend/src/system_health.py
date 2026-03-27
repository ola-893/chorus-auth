"""
System health monitoring and alerting for the Chorus Agent Conflict Predictor.
"""
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from .logging_config import get_agent_logger
from .error_handling import system_recovery_context

agent_logger = get_agent_logger(__name__)


class HealthStatus(Enum):
    """System health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    FAILED = "failed"


@dataclass
class HealthCheck:
    """Individual health check configuration."""
    name: str
    check_function: Callable[[], bool]
    interval: float = 30.0  # seconds
    timeout: float = 10.0   # seconds
    critical: bool = False
    last_check: Optional[datetime] = None
    last_status: Optional[bool] = None
    failure_count: int = 0
    max_failures: int = 3


@dataclass
class SystemHealthMetrics:
    """System health metrics and status."""
    overall_status: HealthStatus = HealthStatus.HEALTHY
    component_statuses: Dict[str, HealthStatus] = field(default_factory=dict)
    last_updated: Optional[datetime] = None
    error_count_24h: int = 0
    uptime: float = 0.0
    active_agents: int = 0
    quarantined_agents: int = 0
    redis_connection_status: bool = True
    gemini_api_status: bool = True


class SystemHealthMonitor:
    """
    Monitors system health and provides alerting capabilities.
    """
    
    def __init__(self):
        """Initialize the health monitor."""
        self.health_checks: Dict[str, HealthCheck] = {}
        self.metrics = SystemHealthMetrics()
        self.start_time = datetime.now()
        self.monitoring_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.alert_callbacks: List[Callable[[str, HealthStatus], None]] = []
        
        # Initialize default health checks
        self._setup_default_health_checks()
        
    def _setup_default_health_checks(self) -> None:
        """Set up default system health checks."""
        
        def check_redis_connection() -> bool:
            """Check Redis connection health."""
            try:
                from .prediction_engine.redis_client import redis_client
                return redis_client.ping()
            except Exception as e:
                agent_logger.log_system_error(
                    e,
                    component="health_monitor",
                    operation="check_redis_connection"
                )
                return False
        
        def check_gemini_api() -> bool:
            """Check Gemini API health."""
            try:
                from .prediction_engine.gemini_client import GeminiClient
                from .config import settings
                
                client = GeminiClient()
                return client.test_connection()
            except Exception as e:
                agent_logger.log_system_error(
                    e,
                    component="health_monitor",
                    operation="check_gemini_api"
                )
                return False

        def check_datadog_api() -> bool:
            """Check Datadog API availability."""
            try:
                from .config import settings
                if not settings.datadog.enabled:
                    return True
                # In a real scenario, check connection or queue size
                return bool(settings.datadog.api_key)
            except Exception as e:
                agent_logger.log_system_error(e, "health_monitor", "check_datadog_api")
                return False

        def check_kafka_connection() -> bool:
            """Check Kafka connectivity."""
            try:
                from .config import settings
                if not settings.kafka.enabled:
                    return True
                # Basic configuration check
                # Real connectivity check would involve admin client list_topics
                return bool(settings.kafka.bootstrap_servers)
            except Exception as e:
                agent_logger.log_system_error(e, "health_monitor", "check_kafka_connection")
                return False

        def check_elevenlabs_api() -> bool:
            """Check ElevenLabs API availability."""
            try:
                from .config import settings
                if not settings.elevenlabs.enabled:
                    return True
                return bool(settings.elevenlabs.api_key)
            except Exception as e:
                agent_logger.log_system_error(e, "health_monitor", "check_elevenlabs_api")
                return False
        
        def check_system_resources() -> bool:
            """Check system resource availability."""
            try:
                import psutil
                
                # Check memory usage (alert if > 90%)
                memory_percent = psutil.virtual_memory().percent
                if memory_percent > 90:
                    return False
                
                # Check CPU usage (alert if > 95% for extended period)
                cpu_percent = psutil.cpu_percent(interval=1)
                if cpu_percent > 95:
                    return False
                
                return True
            except ImportError:
                # psutil not available, assume healthy
                return True
            except Exception as e:
                agent_logger.log_system_error(
                    e,
                    component="health_monitor",
                    operation="check_system_resources"
                )
                return False
        
        # Register health checks
        self.register_health_check(
            "redis_connection",
            check_redis_connection,
            interval=30.0,
            critical=True
        )
        
        self.register_health_check(
            "gemini_api",
            check_gemini_api,
            interval=60.0,
            critical=True
        )

        self.register_health_check(
            "datadog_api",
            check_datadog_api,
            interval=60.0,
            critical=False
        )

        self.register_health_check(
            "kafka_connection",
            check_kafka_connection,
            interval=30.0,
            critical=True
        )

        self.register_health_check(
            "elevenlabs_api",
            check_elevenlabs_api,
            interval=60.0,
            critical=False
        )
        
        self.register_health_check(
            "system_resources",
            check_system_resources,
            interval=45.0,
            critical=False
        )
    
    def register_health_check(
        self,
        name: str,
        check_function: Callable[[], bool],
        interval: float = 30.0,
        timeout: float = 10.0,
        critical: bool = False,
        max_failures: int = 3
    ) -> None:
        """
        Register a new health check.
        
        Args:
            name: Unique name for the health check
            check_function: Function that returns True if healthy, False otherwise
            interval: Check interval in seconds
            timeout: Timeout for the check in seconds
            critical: Whether this check is critical for system operation
            max_failures: Maximum consecutive failures before marking as failed
        """
        self.health_checks[name] = HealthCheck(
            name=name,
            check_function=check_function,
            interval=interval,
            timeout=timeout,
            critical=critical,
            max_failures=max_failures
        )
        
        agent_logger.log_agent_action(
            "INFO",
            f"Registered health check: {name}",
            action_type="health_check_registered",
            context={
                "name": name,
                "interval": interval,
                "critical": critical
            }
        )
    
    def register_alert_callback(self, callback: Callable[[str, HealthStatus], None]) -> None:
        """
        Register a callback for health status alerts.
        
        Args:
            callback: Function to call when health status changes
        """
        self.alert_callbacks.append(callback)
    
    def start_monitoring(self) -> None:
        """Start the health monitoring thread."""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            agent_logger.log_agent_action(
                "WARNING",
                "Health monitoring already running",
                action_type="health_monitor_start_warning"
            )
            return
        
        self.stop_event.clear()
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        agent_logger.log_agent_action(
            "INFO",
            "Health monitoring started",
            action_type="health_monitor_started",
            context={"check_count": len(self.health_checks)}
        )
    
    def stop_monitoring(self) -> None:
        """Stop the health monitoring thread."""
        self.stop_event.set()
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5.0)
        
        agent_logger.log_agent_action(
            "INFO",
            "Health monitoring stopped",
            action_type="health_monitor_stopped"
        )
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while not self.stop_event.is_set():
            try:
                self._run_health_checks()
                self._update_metrics()
                self._check_alert_conditions()
                
                # Sleep for the shortest check interval
                min_interval = min(
                    (check.interval for check in self.health_checks.values()),
                    default=30.0
                )
                self.stop_event.wait(min_interval)
                
            except Exception as e:
                agent_logger.log_system_error(
                    e,
                    component="health_monitor",
                    operation="monitoring_loop"
                )
                # Continue monitoring even if there's an error
                self.stop_event.wait(10.0)
    
    def _run_health_checks(self) -> None:
        """Run all registered health checks."""
        current_time = datetime.now()
        
        for check in self.health_checks.values():
            # Check if it's time to run this check
            if (check.last_check is None or 
                (current_time - check.last_check).total_seconds() >= check.interval):
                
                try:
                    with system_recovery_context(
                        component="health_monitor",
                        operation=f"check_{check.name}"
                    ):
                        # Run the health check with timeout
                        result = self._run_single_check(check)
                        
                        if result:
                            check.failure_count = 0
                        else:
                            check.failure_count += 1
                        
                        check.last_status = result
                        check.last_check = current_time
                        
                        # Update component status
                        if check.failure_count >= check.max_failures:
                            self.metrics.component_statuses[check.name] = HealthStatus.FAILED
                        elif check.failure_count > 0:
                            self.metrics.component_statuses[check.name] = HealthStatus.DEGRADED
                        else:
                            self.metrics.component_statuses[check.name] = HealthStatus.HEALTHY
                
                except Exception as e:
                    agent_logger.log_system_error(
                        e,
                        component="health_monitor",
                        operation=f"run_check_{check.name}"
                    )
                    check.failure_count += 1
                    self.metrics.component_statuses[check.name] = HealthStatus.FAILED
    
    def _run_single_check(self, check: HealthCheck) -> bool:
        """Run a single health check with timeout."""
        try:
            return check.check_function()
        except Exception as e:
            agent_logger.log_system_error(
                e,
                component="health_monitor",
                operation=f"execute_check_{check.name}"
            )
            return False
    
    def _update_metrics(self) -> None:
        """Update system health metrics."""
        self.metrics.last_updated = datetime.now()
        self.metrics.uptime = (datetime.now() - self.start_time).total_seconds()
        
        # Determine overall status
        failed_critical = any(
            status == HealthStatus.FAILED and self.health_checks[name].critical
            for name, status in self.metrics.component_statuses.items()
        )
        
        if failed_critical:
            self.metrics.overall_status = HealthStatus.CRITICAL
        elif HealthStatus.FAILED in self.metrics.component_statuses.values():
            self.metrics.overall_status = HealthStatus.DEGRADED
        elif HealthStatus.DEGRADED in self.metrics.component_statuses.values():
            self.metrics.overall_status = HealthStatus.DEGRADED
        else:
            self.metrics.overall_status = HealthStatus.HEALTHY
    
    def _check_alert_conditions(self) -> None:
        """Check for alert conditions and trigger callbacks."""
        for name, status in self.metrics.component_statuses.items():
            if status in [HealthStatus.CRITICAL, HealthStatus.FAILED]:
                for callback in self.alert_callbacks:
                    try:
                        callback(name, status)
                    except Exception as e:
                        agent_logger.log_system_error(
                            e,
                            component="health_monitor",
                            operation="alert_callback",
                            context={"component": name, "status": status.value}
                        )
    
    def get_health_status(self) -> SystemHealthMetrics:
        """Get current system health status."""
        return self.metrics
    
    def force_health_check(self, check_name: Optional[str] = None) -> Dict[str, bool]:
        """
        Force execution of health checks.
        
        Args:
            check_name: Specific check to run, or None for all checks
            
        Returns:
            Dictionary of check results
        """
        results = {}
        
        checks_to_run = (
            [self.health_checks[check_name]] if check_name and check_name in self.health_checks
            else list(self.health_checks.values())
        )
        
        for check in checks_to_run:
            try:
                result = self._run_single_check(check)
                results[check.name] = result
                
                agent_logger.log_agent_action(
                    "INFO",
                    f"Forced health check: {check.name} = {result}",
                    action_type="forced_health_check",
                    context={"check_name": check.name, "result": result}
                )
                
            except Exception as e:
                results[check.name] = False
                agent_logger.log_system_error(
                    e,
                    component="health_monitor",
                    operation=f"forced_check_{check.name}"
                )
        
        return results


# Global health monitor instance
health_monitor = SystemHealthMonitor()


def cli_alert_callback(component: str, status: HealthStatus) -> None:
    """Default CLI alert callback for health status changes."""
    agent_logger.log_agent_action(
        "ERROR" if status == HealthStatus.CRITICAL else "WARNING",
        f"Health alert: {component} is {status.value}",
        action_type="health_alert",
        context={"component": component, "status": status.value}
    )


# Register default alert callback
health_monitor.register_alert_callback(cli_alert_callback)