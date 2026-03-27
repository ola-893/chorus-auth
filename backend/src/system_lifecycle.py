"""
System lifecycle management for the Chorus Agent Conflict Predictor.
Handles graceful startup, shutdown, and dependency management.
"""
import asyncio
import signal
import sys
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

from .config import Settings, settings
from .logging_config import get_agent_logger
from .system_health import health_monitor, SystemHealthMonitor
from .error_handling import system_recovery_context
from .event_bus import event_bus
from .stream_processor import stream_processor
from .event_bridge import kafka_event_bridge
from .redis_bridge import redis_event_bridge
from .prediction_engine.alert_delivery_engine import alert_delivery_engine
from .integrations.kafka_client import kafka_bus
from .integrations.agentverse.adapter_impl import AgentVerseNetworkAdapter
from .integrations.base import NetworkConfig
from .prediction_engine.redis_client import redis_client
import os

agent_logger = get_agent_logger(__name__)


class SystemState(Enum):
    """System lifecycle states."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"


@dataclass
class DependencyCheck:
    """Dependency check configuration."""
    name: str
    check_function: Callable[[], bool]
    required: bool = True
    timeout: float = 30.0
    retry_count: int = 3
    retry_delay: float = 2.0


class SystemLifecycleManager:
    """
    Manages system startup, shutdown, and dependency checks.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the lifecycle manager.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.state = SystemState.STOPPED
        self.start_time: Optional[datetime] = None
        self.shutdown_callbacks: List[Callable[[], None]] = []
        self.startup_callbacks: List[Callable[[], None]] = []
        self.dependency_checks: Dict[str, DependencyCheck] = {}
        self.health_monitor: Optional[SystemHealthMonitor] = None
        self._shutdown_event = threading.Event()
        self._startup_complete = threading.Event()
        self._health_publisher_thread: Optional[threading.Thread] = None
        
        # Initialize AgentVerse Adapter
        config = NetworkConfig(
            network_id="agentverse",
            api_key=os.getenv("AGENTVERSE_API_KEY"),
            endpoint_url=os.getenv("AGENTVERSE_MONITORED_ADDRESS"),
            polling_interval=float(os.getenv("AGENTVERSE_POLL_INTERVAL", "10.0"))
        )
        self.agentverse_adapter = AgentVerseNetworkAdapter(config)
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        # Setup default dependency checks
        self._setup_default_dependency_checks()
        
        # Register observability initialization
        self._setup_observability_callbacks()

    def _start_health_publisher(self):
        """Start a background thread to publish health updates."""
        def publisher_loop():
            while not self._shutdown_event.is_set():
                try:
                    status = self.get_status()
                    event_bus.publish("system_health", {
                        "type": "system_status",
                        "data": status,
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    })
                except Exception as e:
                    agent_logger.log_system_error(e, "lifecycle_manager", "health_publisher")
                
                # Wait for next interval
                self._shutdown_event.wait(5.0) # Publish every 5 seconds

        self._health_publisher_thread = threading.Thread(target=publisher_loop, daemon=True)
        self._health_publisher_thread.start()
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            agent_logger.log_agent_action(
                "INFO",
                f"Received signal {signum}, initiating graceful shutdown",
                action_type="signal_received",
                context={"signal": signum}
            )
            self.shutdown()
        
        # Handle SIGTERM and SIGINT
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # Handle SIGUSR1 for health check
        def health_check_handler(signum, frame):
            if self.health_monitor:
                results = self.health_monitor.force_health_check()
                agent_logger.log_agent_action(
                    "INFO",
                    f"Health check results: {results}",
                    action_type="forced_health_check",
                    context={"results": results}
                )
        
        signal.signal(signal.SIGUSR1, health_check_handler)
    
    def _setup_default_dependency_checks(self) -> None:
        """Setup default dependency checks."""
        
        def check_redis_connection() -> bool:
            """Check Redis connection."""
            try:
                from .prediction_engine.redis_client import RedisClient
                client = RedisClient()
                return client.ping()
            except Exception as e:
                agent_logger.log_system_error(
                    e,
                    component="lifecycle_manager",
                    operation="check_redis_connection"
                )
                return False
        
        def check_gemini_api() -> bool:
            """Check Gemini API availability."""
            try:
                from .prediction_engine.gemini_client import GeminiClient
                client = GeminiClient()
                return client.test_connection()
            except Exception as e:
                agent_logger.log_system_error(
                    e,
                    component="lifecycle_manager",
                    operation="check_gemini_api"
                )
                return False
        
        def check_configuration() -> bool:
            """Check configuration validity."""
            try:
                from .config_validator import ConfigurationValidator
                validator = ConfigurationValidator(self.settings)
                results = validator.validate_all()
                return results["overall_status"] != "failed"
            except Exception as e:
                agent_logger.log_system_error(
                    e,
                    component="lifecycle_manager",
                    operation="check_configuration"
                )
                return False
        
        def check_datadog_connection() -> bool:
            """Check Datadog API connectivity."""
            try:
                from .integrations.datadog_client import datadog_client
                if not datadog_client.enabled:
                    return True  # Not required if disabled
                
                # Test connection by sending a test metric
                datadog_client.send_metric("chorus.system.health_check", 1.0, metric_type="count")
                return True
            except Exception as e:
                agent_logger.log_system_error(
                    e,
                    component="lifecycle_manager",
                    operation="check_datadog_connection"
                )
                return False
        
        # Register dependency checks
        self.register_dependency_check(
            "configuration",
            check_configuration,
            required=True,
            timeout=10.0
        )
        
        self.register_dependency_check(
            "redis_connection",
            check_redis_connection,
            required=True,
            timeout=15.0
        )
        
        self.register_dependency_check(
            "gemini_api",
            check_gemini_api,
            required=False,  # Optional - system can run with degraded conflict prediction
            timeout=30.0
        )
        
        self.register_dependency_check(
            "datadog_connection",
            check_datadog_connection,
            required=False,  # Optional for graceful degradation
            timeout=15.0
        )
    
    def register_dependency_check(
        self,
        name: str,
        check_function: Callable[[], bool],
        required: bool = True,
        timeout: float = 30.0,
        retry_count: int = 3,
        retry_delay: float = 2.0
    ) -> None:
        """
        Register a dependency check.
        
        Args:
            name: Unique name for the dependency
            check_function: Function that returns True if dependency is available
            required: Whether this dependency is required for startup
            timeout: Timeout for the check in seconds
            retry_count: Number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.dependency_checks[name] = DependencyCheck(
            name=name,
            check_function=check_function,
            required=required,
            timeout=timeout,
            retry_count=retry_count,
            retry_delay=retry_delay
        )
        
        agent_logger.log_agent_action(
            "INFO",
            f"Registered dependency check: {name}",
            action_type="dependency_registered",
            context={
                "name": name,
                "required": required,
                "timeout": timeout
            }
        )
    
    def register_startup_callback(self, callback: Callable[[], None]) -> None:
        """
        Register a callback to be called during startup.
        
        Args:
            callback: Function to call during startup
        """
        self.startup_callbacks.append(callback)
    
    def register_shutdown_callback(self, callback: Callable[[], None]) -> None:
        """
        Register a callback to be called during shutdown.
        
        Args:
            callback: Function to call during shutdown
        """
        self.shutdown_callbacks.append(callback)
    
    def startup(self) -> bool:
        """
        Start the system with dependency checks.
        
        Returns:
            True if startup successful, False otherwise
        """
        if self.state != SystemState.STOPPED:
            agent_logger.log_agent_action(
                "WARNING",
                f"Cannot start system in state: {self.state.value}",
                action_type="startup_warning"
            )
            return False
        
        self.state = SystemState.STARTING
        self.start_time = datetime.now()
        
        agent_logger.log_agent_action(
            "INFO",
            "Starting Chorus Agent Conflict Predictor system",
            action_type="system_startup_begin",
            context={
                "environment": self.settings.environment.value,
                "debug": self.settings.debug
            }
        )
        
        try:
            # Run dependency checks
            if not self._run_dependency_checks():
                self.state = SystemState.FAILED
                return False
            
            # Initialize health monitoring
            self._initialize_health_monitoring()
            
            # Create Kafka topics
            if self.settings.kafka.enabled:
                try:
                    topics = [
                        self.settings.kafka.agent_messages_topic,
                        self.settings.kafka.agent_decisions_topic,
                        self.settings.kafka.system_alerts_topic,
                        self.settings.kafka.causal_graph_updates_topic,
                        self.settings.kafka.analytics_metrics_topic
                    ]
                    kafka_bus.create_topics(topics)
                    agent_logger.log_agent_action("INFO", "Kafka topics creation initiated", action_type="kafka_topics_init")
                except Exception as e:
                    agent_logger.log_system_error(e, "lifecycle_manager", "create_topics")

            # Start Stream Processor
            try:
                stream_processor.start()
                agent_logger.log_agent_action("INFO", "Stream Processor started", action_type="stream_processor_init")
                
                # Register shutdown callback for Stream Processor
                self.register_shutdown_callback(stream_processor.stop)
            except Exception as e:
                agent_logger.log_system_error(e, "lifecycle_manager", "start_stream_processor")

            # Start Alert Delivery Engine
            try:
                alert_delivery_engine.start()
                agent_logger.log_agent_action("INFO", "Alert Delivery Engine started", action_type="alert_delivery_init")
                self.register_shutdown_callback(alert_delivery_engine.stop)
            except Exception as e:
                agent_logger.log_system_error(e, "lifecycle_manager", "start_alert_delivery")

            # Start Kafka Event Bridge
            try:
                kafka_event_bridge.start()
                agent_logger.log_agent_action("INFO", "Kafka Event Bridge started", action_type="event_bridge_init")
                
                # Register shutdown callback for Event Bridge
                self.register_shutdown_callback(kafka_event_bridge.stop)
            except Exception as e:
                agent_logger.log_system_error(e, "lifecycle_manager", "start_event_bridge")

            # Start Redis Event Bridge (Cross-process synchronization)
            try:
                redis_event_bridge.start()
                agent_logger.log_agent_action("INFO", "Redis Event Bridge started", action_type="redis_bridge_init")
                self.register_shutdown_callback(redis_event_bridge.stop)
            except Exception as e:
                agent_logger.log_system_error(e, "lifecycle_manager", "start_redis_bridge")

            # Start AgentVerse Adapter
            try:
                def run_adapter_loop():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.agentverse_adapter.start())
                    loop.close()

                adapter_thread = threading.Thread(target=run_adapter_loop, daemon=True)
                adapter_thread.start()
                
                agent_logger.log_agent_action("INFO", "AgentVerse Adapter started", action_type="agentverse_adapter_init")
                
                # Register shutdown callback (async wrapper needed if stop is async)
                # But BaseNetworkAdapter.stop is async.
                # Shutdown callbacks in this system seem to be synchronous functions?
                # Looking at 'register_shutdown_callback(callback: Callable[[], None])'.
                # We need a sync wrapper for stop.
                def stop_adapter_sync():
                    asyncio.run(self.agentverse_adapter.stop())

                self.register_shutdown_callback(stop_adapter_sync)
            except Exception as e:
                agent_logger.log_system_error(e, "lifecycle_manager", "start_agentverse_adapter")

            # Start performance monitoring
            try:
                from .performance_optimizer import performance_monitor, connection_pool_manager
                performance_monitor.start_monitoring()
                agent_logger.log_agent_action("INFO", "Performance monitoring started", action_type="performance_monitor_init")
                
                # Register shutdown callback for performance monitor
                self.register_shutdown_callback(performance_monitor.stop_monitoring)
            except ImportError:
                agent_logger.log_agent_action("WARNING", "Performance monitoring not available", action_type="performance_monitor_unavailable")
            except Exception as e:
                agent_logger.log_system_error(e, "lifecycle_manager", "start_performance_monitor")

            # Start stream monitoring
            try:
                from .stream_monitoring import stream_monitor
                stream_monitor.start_monitoring()
                agent_logger.log_agent_action("INFO", "Stream monitoring started", action_type="stream_monitor_init")
                
                # Register shutdown callback for stream monitor
                self.register_shutdown_callback(stream_monitor.stop_monitoring)
            except ImportError:
                agent_logger.log_agent_action("WARNING", "Stream monitoring not available", action_type="stream_monitor_unavailable")
            except Exception as e:
                agent_logger.log_system_error(e, "lifecycle_manager", "start_stream_monitor")

            # Start health publisher
            self._start_health_publisher()
            
            # Run startup callbacks
            self._run_startup_callbacks()
            
            # Mark startup as complete
            self.state = SystemState.RUNNING
            self._startup_complete.set()
            
            agent_logger.log_agent_action(
                "INFO",
                "System startup completed successfully",
                action_type="system_startup_complete",
                context={
                    "startup_time": (datetime.now() - self.start_time).total_seconds(),
                    "dependency_count": len(self.dependency_checks)
                }
            )
            
            return True
            
        except Exception as e:
            self.state = SystemState.FAILED
            agent_logger.log_system_error(
                e,
                component="lifecycle_manager",
                operation="startup"
            )
            return False
    
    def _run_dependency_checks(self) -> bool:
        """
        Run all dependency checks.
        
        Returns:
            True if all required dependencies are available
        """
        agent_logger.log_agent_action(
            "INFO",
            f"Running {len(self.dependency_checks)} dependency checks",
            action_type="dependency_checks_begin"
        )
        
        failed_required = []
        failed_optional = []
        
        for check in self.dependency_checks.values():
            success = self._run_single_dependency_check(check)
            
            if not success:
                if check.required:
                    failed_required.append(check.name)
                else:
                    failed_optional.append(check.name)
        
        # Log results
        if failed_optional:
            agent_logger.log_agent_action(
                "WARNING",
                f"Optional dependencies failed: {failed_optional}",
                action_type="optional_dependencies_failed",
                context={"failed_dependencies": failed_optional}
            )
        
        if failed_required:
            agent_logger.log_agent_action(
                "ERROR",
                f"Required dependencies failed: {failed_required}",
                action_type="required_dependencies_failed",
                context={"failed_dependencies": failed_required}
            )
            return False
        
        agent_logger.log_agent_action(
            "INFO",
            "All dependency checks passed",
            action_type="dependency_checks_complete"
        )
        
        return True
    
    def _run_single_dependency_check(self, check: DependencyCheck) -> bool:
        """
        Run a single dependency check with retries.
        
        Args:
            check: Dependency check to run
            
        Returns:
            True if check passed, False otherwise
        """
        for attempt in range(check.retry_count + 1):
            try:
                agent_logger.log_agent_action(
                    "DEBUG",
                    f"Running dependency check: {check.name} (attempt {attempt + 1})",
                    action_type="dependency_check_attempt",
                    context={
                        "dependency": check.name,
                        "attempt": attempt + 1,
                        "max_attempts": check.retry_count + 1
                    }
                )
                
                # Run the check with timeout
                result = self._run_with_timeout(check.check_function, check.timeout)
                
                if result:
                    agent_logger.log_agent_action(
                        "INFO",
                        f"Dependency check passed: {check.name}",
                        action_type="dependency_check_passed",
                        context={"dependency": check.name}
                    )
                    return True
                
                # If not the last attempt, wait before retrying
                if attempt < check.retry_count:
                    agent_logger.log_agent_action(
                        "WARNING",
                        f"Dependency check failed: {check.name}, retrying in {check.retry_delay}s",
                        action_type="dependency_check_retry",
                        context={
                            "dependency": check.name,
                            "retry_delay": check.retry_delay
                        }
                    )
                    time.sleep(check.retry_delay)
                
            except Exception as e:
                agent_logger.log_system_error(
                    e,
                    component="lifecycle_manager",
                    operation=f"dependency_check_{check.name}",
                    context={"attempt": attempt + 1}
                )
                
                if attempt < check.retry_count:
                    time.sleep(check.retry_delay)
        
        agent_logger.log_agent_action(
            "ERROR",
            f"Dependency check failed after {check.retry_count + 1} attempts: {check.name}",
            action_type="dependency_check_failed",
            context={
                "dependency": check.name,
                "attempts": check.retry_count + 1
            }
        )
        
        return False
    
    def _run_with_timeout(self, func: Callable[[], bool], timeout: float) -> bool:
        """
        Run a function with timeout.
        
        Args:
            func: Function to run
            timeout: Timeout in seconds
            
        Returns:
            Function result or False if timeout
        """
        result = [False]
        exception = [None]
        
        def target():
            try:
                result[0] = func()
            except Exception as e:
                exception[0] = e
        
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout)
        
        if thread.is_alive():
            # Timeout occurred
            return False
        
        if exception[0]:
            raise exception[0]
        
        return result[0]
    
    def _initialize_health_monitoring(self) -> None:
        """Initialize health monitoring."""
        if self.settings.health_check.enabled:
            global health_monitor
            self.health_monitor = health_monitor
            self.health_monitor.start_monitoring()
            
            agent_logger.log_agent_action(
                "INFO",
                "Health monitoring initialized",
                action_type="health_monitoring_initialized"
            )
    
    def _run_startup_callbacks(self) -> None:
        """Run all startup callbacks."""
        for callback in self.startup_callbacks:
            try:
                callback()
                agent_logger.log_agent_action(
                    "DEBUG",
                    f"Startup callback executed: {callback.__name__}",
                    action_type="startup_callback_executed"
                )
            except Exception as e:
                agent_logger.log_system_error(
                    e,
                    component="lifecycle_manager",
                    operation=f"startup_callback_{callback.__name__}"
                )
    
    def shutdown(self) -> None:
        """Gracefully shutdown the system."""
        if self.state in [SystemState.STOPPED, SystemState.STOPPING]:
            return
        
        self.state = SystemState.STOPPING
        
        agent_logger.log_agent_action(
            "INFO",
            "Initiating system shutdown",
            action_type="system_shutdown_begin"
        )
        
        try:
            # Run shutdown callbacks in reverse order
            for callback in reversed(self.shutdown_callbacks):
                try:
                    callback()
                    agent_logger.log_agent_action(
                        "DEBUG",
                        f"Shutdown callback executed: {callback.__name__}",
                        action_type="shutdown_callback_executed"
                    )
                except Exception as e:
                    agent_logger.log_system_error(
                        e,
                        component="lifecycle_manager",
                        operation=f"shutdown_callback_{callback.__name__}"
                    )
            
            # Stop health monitoring
            if self.health_monitor:
                self.health_monitor.stop_monitoring()
                agent_logger.log_agent_action(
                    "INFO",
                    "Health monitoring stopped",
                    action_type="health_monitoring_stopped"
                )
            
            # Set shutdown event
            self._shutdown_event.set()
            
            self.state = SystemState.STOPPED
            
            uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
            
            agent_logger.log_agent_action(
                "INFO",
                "System shutdown completed",
                action_type="system_shutdown_complete",
                context={"uptime": uptime}
            )
            
        except Exception as e:
            agent_logger.log_system_error(
                e,
                component="lifecycle_manager",
                operation="shutdown"
            )
            self.state = SystemState.FAILED
    
    def wait_for_shutdown(self) -> None:
        """Wait for shutdown signal."""
        self._shutdown_event.wait()
    
    def is_running(self) -> bool:
        """Check if system is running."""
        return self.state == SystemState.RUNNING
    
    def is_healthy(self) -> bool:
        """Check if system is healthy."""
        if not self.is_running():
            return False
        
        if self.health_monitor:
            status = self.health_monitor.get_health_status()
            return status.overall_status.value in ["healthy", "degraded"]
        
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get system status information.
        
        Returns:
            Dictionary containing system status
        """
        uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        status = {
            "state": self.state.value,
            "uptime": uptime,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "is_healthy": self.is_healthy(),
            "dependency_checks": len(self.dependency_checks),
            "startup_callbacks": len(self.startup_callbacks),
            "shutdown_callbacks": len(self.shutdown_callbacks)
        }
        
        if self.health_monitor:
            health_status = self.health_monitor.get_health_status()
            status["health"] = {
                "overall_status": health_status.overall_status.value,
                "component_statuses": {
                    name: status.value 
                    for name, status in health_status.component_statuses.items()
                },
                "last_updated": health_status.last_updated.isoformat() if health_status.last_updated else None
            }
        
        return status
    
    def _setup_observability_callbacks(self):
        """Setup observability initialization callbacks."""
        def initialize_observability():
            """Initialize observability components during startup."""
            try:
                # Initialize Datadog client
                from .integrations.datadog_client import datadog_client
                if datadog_client.enabled:
                    agent_logger.log_agent_action(
                        "INFO",
                        "Datadog client initialized for observability",
                        action_type="observability_init",
                        context={"component": "datadog"}
                    )
                    
                    # Send startup metric
                    datadog_client.send_metric(
                        "chorus.system.startup",
                        1.0,
                        tags=["component:system_lifecycle"],
                        metric_type="count"
                    )
                
                # Initialize circuit breaker monitoring
                from .error_handling import gemini_circuit_breaker, redis_circuit_breaker
                
                # Subscribe to circuit breaker events
                def on_circuit_breaker_event(data):
                    """Handle circuit breaker state changes."""
                    try:
                        if datadog_client.enabled:
                            datadog_client.send_metric(
                                f"chorus.circuit_breaker.{data.get('state', 'unknown').lower()}",
                                1.0,
                                tags=[f"service:{data.get('service', 'unknown')}"],
                                metric_type="count"
                            )
                            
                            datadog_client.send_log(
                                f"Circuit breaker state changed: {data.get('service')} -> {data.get('state')}",
                                level="WARN" if data.get('state') == 'OPEN' else "INFO",
                                context=data
                            )
                    except Exception as e:
                        agent_logger.log_system_error(e, "observability", "circuit_breaker_event")
                
                event_bus.subscribe("circuit_breaker_state_change", on_circuit_breaker_event)
                
                # Initialize trust score observability
                def on_trust_score_update(data):
                    """Handle trust score update events."""
                    try:
                        if datadog_client.enabled:
                            datadog_client.track_trust_score_change(
                                agent_id=data.get('agent_id'),
                                old_score=data.get('old_score'),
                                new_score=data.get('new_score'),
                                reason=data.get('reason')
                            )
                    except Exception as e:
                        agent_logger.log_system_error(e, "observability", "trust_score_event")
                
                event_bus.subscribe("trust_score_update", on_trust_score_update)
                
                # Initialize conflict prediction observability
                def on_conflict_prediction(data):
                    """Handle conflict prediction events."""
                    try:
                        if datadog_client.enabled:
                            datadog_client.track_conflict_prediction(
                                conflict_id=data.get('conflict_id'),
                                risk_score=data.get('risk_score'),
                                affected_agents=data.get('affected_agents', [])
                            )
                    except Exception as e:
                        agent_logger.log_system_error(e, "observability", "conflict_prediction_event")
                
                event_bus.subscribe("conflict_prediction", on_conflict_prediction)
                
                agent_logger.log_agent_action(
                    "INFO",
                    "Observability components initialized successfully",
                    action_type="observability_init_complete"
                )
                
            except Exception as e:
                agent_logger.log_system_error(
                    e,
                    component="lifecycle_manager",
                    operation="initialize_observability"
                )
        
        def shutdown_observability():
            """Cleanup observability components during shutdown."""
            try:
                from .integrations.datadog_client import datadog_client
                if datadog_client.enabled:
                    # Send shutdown metric
                    datadog_client.send_metric(
                        "chorus.system.shutdown",
                        1.0,
                        tags=["component:system_lifecycle"],
                        metric_type="count"
                    )
                    
                    agent_logger.log_agent_action(
                        "INFO",
                        "Observability components shutdown complete",
                        action_type="observability_shutdown"
                    )
            except Exception as e:
                agent_logger.log_system_error(
                    e,
                    component="lifecycle_manager",
                    operation="shutdown_observability"
                )
        
        # Register callbacks
        self.register_startup_callback(initialize_observability)
        self.register_shutdown_callback(shutdown_observability)


@asynccontextmanager
async def system_lifespan(app_settings: Optional[Settings] = None):
    """
    Async context manager for system lifecycle management.
    
    Args:
        app_settings: Optional settings override
    """
    lifecycle_manager = SystemLifecycleManager(app_settings or settings)
    
    try:
        # Startup
        if not lifecycle_manager.startup():
            raise RuntimeError("System startup failed")
        
        yield lifecycle_manager
        
    finally:
        # Shutdown
        lifecycle_manager.shutdown()


# Global lifecycle manager instance
lifecycle_manager = SystemLifecycleManager(settings)


def main_startup_procedure() -> bool:
    """
    Main startup procedure for the application.
    
    Returns:
        True if startup successful, False otherwise
    """
    return lifecycle_manager.startup()


def main_shutdown_procedure() -> None:
    """Main shutdown procedure for the application."""
    lifecycle_manager.shutdown()


def wait_for_shutdown() -> None:
    """Wait for shutdown signal."""
    lifecycle_manager.wait_for_shutdown()


def get_system_status() -> Dict[str, Any]:
    """Get current system status."""
    return lifecycle_manager.get_status()


if __name__ == "__main__":
    """CLI entry point for system lifecycle management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Chorus Agent Conflict Predictor System Lifecycle")
    parser.add_argument("command", choices=["start", "status", "health"], help="Command to execute")
    parser.add_argument("--env-file", help="Path to .env file")
    
    args = parser.parse_args()
    
    # Load settings
    if args.env_file:
        from .config import load_settings
        app_settings = load_settings(args.env_file)
        lifecycle_manager = SystemLifecycleManager(app_settings)
    
    if args.command == "start":
        print("Starting Chorus Agent Conflict Predictor...")
        if lifecycle_manager.startup():
            print("System started successfully. Press Ctrl+C to shutdown.")
            try:
                lifecycle_manager.wait_for_shutdown()
            except KeyboardInterrupt:
                pass
            finally:
                lifecycle_manager.shutdown()
        else:
            print("System startup failed.")
            sys.exit(1)
    
    elif args.command == "status":
        status = lifecycle_manager.get_status()
        print(f"System State: {status['state']}")
        print(f"Uptime: {status['uptime']:.2f} seconds")
        print(f"Healthy: {status['is_healthy']}")
        
        if "health" in status:
            print(f"Health Status: {status['health']['overall_status']}")
            for component, comp_status in status['health']['component_statuses'].items():
                print(f"  {component}: {comp_status}")
    
    elif args.command == "health":
        if lifecycle_manager.health_monitor:
            results = lifecycle_manager.health_monitor.force_health_check()
            print("Health Check Results:")
            for check_name, result in results.items():
                status_symbol = "✓" if result else "✗"
                print(f"  {status_symbol} {check_name}: {'PASS' if result else 'FAIL'}")
        else:
            print("Health monitoring not available.")