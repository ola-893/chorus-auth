"""
Comprehensive monitoring and alerting for stream processing performance.
"""
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from collections import deque, defaultdict
from enum import Enum

from .config import settings
from .logging_config import get_agent_logger
from .integrations.kafka_client import kafka_bus
from .stream_analytics import stream_analytics
from .performance_optimizer import performance_monitor

agent_logger = get_agent_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class StreamAlert:
    """Stream processing alert."""
    alert_id: str
    severity: AlertSeverity
    title: str
    description: str
    metric_name: str
    current_value: float
    threshold_value: float
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolution_time: Optional[datetime] = None


@dataclass
class StreamMetrics:
    """Comprehensive stream processing metrics."""
    # Throughput metrics
    messages_per_second: float = 0.0
    bytes_per_second: float = 0.0
    
    # Latency metrics
    avg_processing_latency_ms: float = 0.0
    p95_processing_latency_ms: float = 0.0
    p99_processing_latency_ms: float = 0.0
    
    # Error metrics
    error_rate: float = 0.0
    timeout_rate: float = 0.0
    retry_rate: float = 0.0
    
    # Kafka-specific metrics
    kafka_lag: int = 0
    kafka_connection_status: bool = True
    producer_queue_size: int = 0
    consumer_group_lag: int = 0
    
    # Resource metrics
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    thread_count: int = 0
    
    # Business metrics
    conflict_detection_rate: float = 0.0
    quarantine_rate: float = 0.0
    pattern_detection_rate: float = 0.0
    
    timestamp: datetime = field(default_factory=datetime.now)


class StreamPerformanceMonitor:
    """Advanced monitoring for stream processing performance."""
    
    def __init__(self):
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.metrics_history: deque = deque(maxlen=300)  # 5 minutes at 1-second intervals
        self.active_alerts: Dict[str, StreamAlert] = {}
        self.alert_callbacks: List[Callable[[StreamAlert], None]] = []
        
        # Thresholds for alerting
        self.thresholds = {
            'max_processing_latency_ms': 1000.0,
            'max_error_rate': 0.05,  # 5%
            'min_throughput_mps': 1.0,  # messages per second
            'max_kafka_lag': 1000,
            'max_cpu_usage': 85.0,
            'max_memory_usage': 80.0,
            'max_timeout_rate': 0.02,  # 2%
        }
        
        # Metric collectors
        self.latency_samples: deque = deque(maxlen=1000)
        self.error_count = 0
        self.timeout_count = 0
        self.retry_count = 0
        self.message_count = 0
        self.last_reset_time = time.time()
        
    def start_monitoring(self):
        """Start stream performance monitoring."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        agent_logger.log_agent_action(
            "INFO",
            "Stream performance monitoring started",
            action_type="stream_monitor_start"
        )
    
    def stop_monitoring(self):
        """Stop stream performance monitoring."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
    
    def record_processing_latency(self, latency_ms: float):
        """Record processing latency sample."""
        self.latency_samples.append(latency_ms)
    
    def record_message_processed(self):
        """Record a successfully processed message."""
        self.message_count += 1
    
    def record_error(self):
        """Record a processing error."""
        self.error_count += 1
    
    def record_timeout(self):
        """Record a processing timeout."""
        self.timeout_count += 1
    
    def record_retry(self):
        """Record a retry attempt."""
        self.retry_count += 1
    
    def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring:
            try:
                # Collect current metrics
                metrics = self._collect_stream_metrics()
                self.metrics_history.append(metrics)
                
                # Check for alert conditions
                self._check_alert_conditions(metrics)
                
                # Reset counters every minute
                if time.time() - self.last_reset_time >= 60:
                    self._reset_counters()
                
                time.sleep(1.0)
                
            except Exception as e:
                agent_logger.log_system_error(e, "stream_monitor", "monitoring_loop")
                time.sleep(5.0)
    
    def _collect_stream_metrics(self) -> StreamMetrics:
        """Collect comprehensive stream processing metrics."""
        try:
            # Get basic stream analytics
            analytics = stream_analytics.calculate_metrics()
            
            # Calculate rates
            time_window = min(60, time.time() - self.last_reset_time)
            if time_window > 0:
                messages_per_second = self.message_count / time_window
                error_rate = self.error_count / max(1, self.message_count)
                timeout_rate = self.timeout_count / max(1, self.message_count)
                retry_rate = self.retry_count / max(1, self.message_count)
            else:
                messages_per_second = error_rate = timeout_rate = retry_rate = 0.0
            
            # Calculate latency percentiles
            if self.latency_samples:
                sorted_latencies = sorted(self.latency_samples)
                p95_idx = int(len(sorted_latencies) * 0.95)
                p99_idx = int(len(sorted_latencies) * 0.99)
                avg_latency = sum(sorted_latencies) / len(sorted_latencies)
                p95_latency = sorted_latencies[p95_idx] if p95_idx < len(sorted_latencies) else 0
                p99_latency = sorted_latencies[p99_idx] if p99_idx < len(sorted_latencies) else 0
            else:
                avg_latency = p95_latency = p99_latency = 0.0
            
            # Get Kafka metrics
            kafka_metrics = self._get_kafka_metrics()
            
            # Get resource metrics
            resource_metrics = self._get_resource_metrics()
            
            return StreamMetrics(
                messages_per_second=messages_per_second,
                bytes_per_second=messages_per_second * 1024,  # Estimate
                avg_processing_latency_ms=avg_latency,
                p95_processing_latency_ms=p95_latency,
                p99_processing_latency_ms=p99_latency,
                error_rate=error_rate,
                timeout_rate=timeout_rate,
                retry_rate=retry_rate,
                kafka_lag=kafka_metrics.get('lag', 0),
                kafka_connection_status=kafka_metrics.get('connected', True),
                producer_queue_size=kafka_metrics.get('queue_size', 0),
                consumer_group_lag=kafka_metrics.get('group_lag', 0),
                cpu_usage=resource_metrics.get('cpu', 0.0),
                memory_usage=resource_metrics.get('memory', 0.0),
                thread_count=resource_metrics.get('threads', 0),
                conflict_detection_rate=analytics.get('conflict_rate', 0.0),
                quarantine_rate=0.0,  # Would need to track from intervention engine
                pattern_detection_rate=len(analytics.get('anomalies', [])) / time_window if time_window > 0 else 0.0
            )
            
        except Exception as e:
            agent_logger.log_system_error(e, "stream_monitor", "collect_metrics")
            return StreamMetrics()
    
    def _get_kafka_metrics(self) -> Dict[str, Any]:
        """Get Kafka-specific metrics."""
        try:
            # Get buffer status from Kafka client
            buffer_status = kafka_bus.get_buffer_status()
            
            return {
                'connected': buffer_status.get('is_connected', True),
                'queue_size': buffer_status.get('size', 0),
                'lag': 0,  # Would need to implement consumer lag tracking
                'group_lag': 0  # Would need to implement group lag tracking
            }
        except Exception as e:
            agent_logger.log_system_error(e, "stream_monitor", "get_kafka_metrics")
            return {}
    
    def _get_resource_metrics(self) -> Dict[str, Any]:
        """Get resource usage metrics."""
        try:
            import psutil
            
            # Get process-specific metrics
            process = psutil.Process()
            
            return {
                'cpu': process.cpu_percent(),
                'memory': process.memory_percent(),
                'threads': process.num_threads()
            }
        except Exception as e:
            agent_logger.log_system_error(e, "stream_monitor", "get_resource_metrics")
            return {}
    
    def _reset_counters(self):
        """Reset rate counters."""
        self.message_count = 0
        self.error_count = 0
        self.timeout_count = 0
        self.retry_count = 0
        self.last_reset_time = time.time()
    
    def _check_alert_conditions(self, metrics: StreamMetrics):
        """Check for alert conditions and generate alerts."""
        alerts_to_create = []
        alerts_to_resolve = []
        
        # Processing latency alerts
        if metrics.p95_processing_latency_ms > self.thresholds['max_processing_latency_ms']:
            alerts_to_create.append(StreamAlert(
                alert_id="high_processing_latency",
                severity=AlertSeverity.WARNING if metrics.p95_processing_latency_ms < 2000 else AlertSeverity.CRITICAL,
                title="High Processing Latency",
                description=f"P95 processing latency is {metrics.p95_processing_latency_ms:.1f}ms",
                metric_name="p95_processing_latency_ms",
                current_value=metrics.p95_processing_latency_ms,
                threshold_value=self.thresholds['max_processing_latency_ms']
            ))
        else:
            alerts_to_resolve.append("high_processing_latency")
        
        # Error rate alerts
        if metrics.error_rate > self.thresholds['max_error_rate']:
            alerts_to_create.append(StreamAlert(
                alert_id="high_error_rate",
                severity=AlertSeverity.CRITICAL,
                title="High Error Rate",
                description=f"Error rate is {metrics.error_rate:.2%}",
                metric_name="error_rate",
                current_value=metrics.error_rate,
                threshold_value=self.thresholds['max_error_rate']
            ))
        else:
            alerts_to_resolve.append("high_error_rate")
        
        # Throughput alerts
        if metrics.messages_per_second < self.thresholds['min_throughput_mps']:
            alerts_to_create.append(StreamAlert(
                alert_id="low_throughput",
                severity=AlertSeverity.WARNING,
                title="Low Message Throughput",
                description=f"Throughput is {metrics.messages_per_second:.1f} msg/s",
                metric_name="messages_per_second",
                current_value=metrics.messages_per_second,
                threshold_value=self.thresholds['min_throughput_mps']
            ))
        else:
            alerts_to_resolve.append("low_throughput")
        
        # Kafka connectivity alerts
        if not metrics.kafka_connection_status:
            alerts_to_create.append(StreamAlert(
                alert_id="kafka_disconnected",
                severity=AlertSeverity.CRITICAL,
                title="Kafka Connection Lost",
                description="Kafka connection is not available",
                metric_name="kafka_connection_status",
                current_value=0.0,
                threshold_value=1.0
            ))
        else:
            alerts_to_resolve.append("kafka_disconnected")
        
        # Resource usage alerts
        if metrics.cpu_usage > self.thresholds['max_cpu_usage']:
            alerts_to_create.append(StreamAlert(
                alert_id="high_cpu_usage",
                severity=AlertSeverity.WARNING,
                title="High CPU Usage",
                description=f"CPU usage is {metrics.cpu_usage:.1f}%",
                metric_name="cpu_usage",
                current_value=metrics.cpu_usage,
                threshold_value=self.thresholds['max_cpu_usage']
            ))
        else:
            alerts_to_resolve.append("high_cpu_usage")
        
        if metrics.memory_usage > self.thresholds['max_memory_usage']:
            alerts_to_create.append(StreamAlert(
                alert_id="high_memory_usage",
                severity=AlertSeverity.WARNING,
                title="High Memory Usage",
                description=f"Memory usage is {metrics.memory_usage:.1f}%",
                metric_name="memory_usage",
                current_value=metrics.memory_usage,
                threshold_value=self.thresholds['max_memory_usage']
            ))
        else:
            alerts_to_resolve.append("high_memory_usage")
        
        # Create new alerts
        for alert in alerts_to_create:
            if alert.alert_id not in self.active_alerts:
                self.active_alerts[alert.alert_id] = alert
                self._trigger_alert(alert)
        
        # Resolve alerts
        for alert_id in alerts_to_resolve:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.resolved = True
                alert.resolution_time = datetime.now()
                del self.active_alerts[alert_id]
                self._resolve_alert(alert)
    
    def _trigger_alert(self, alert: StreamAlert):
        """Trigger an alert."""
        agent_logger.log_agent_action(
            "ERROR" if alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY] else "WARNING",
            f"Stream processing alert: {alert.title}",
            action_type="stream_alert_triggered",
            context={
                "alert_id": alert.alert_id,
                "severity": alert.severity.value,
                "description": alert.description,
                "current_value": alert.current_value,
                "threshold": alert.threshold_value
            }
        )
        
        # Notify callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                agent_logger.log_system_error(e, "stream_monitor", "alert_callback")
    
    def _resolve_alert(self, alert: StreamAlert):
        """Resolve an alert."""
        agent_logger.log_agent_action(
            "INFO",
            f"Stream processing alert resolved: {alert.title}",
            action_type="stream_alert_resolved",
            context={
                "alert_id": alert.alert_id,
                "duration_seconds": (alert.resolution_time - alert.timestamp).total_seconds()
            }
        )
    
    def register_alert_callback(self, callback: Callable[[StreamAlert], None]):
        """Register a callback for stream alerts."""
        self.alert_callbacks.append(callback)
    
    def get_current_metrics(self) -> Optional[StreamMetrics]:
        """Get the most recent metrics."""
        return self.metrics_history[-1] if self.metrics_history else None
    
    def get_metrics_history(self, minutes: int = 5) -> List[StreamMetrics]:
        """Get metrics history for the specified time period."""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [m for m in self.metrics_history if m.timestamp >= cutoff_time]
    
    def get_active_alerts(self) -> List[StreamAlert]:
        """Get all active alerts."""
        return list(self.active_alerts.values())
    
    def update_thresholds(self, new_thresholds: Dict[str, float]):
        """Update alert thresholds."""
        self.thresholds.update(new_thresholds)
        agent_logger.log_agent_action(
            "INFO",
            "Stream monitoring thresholds updated",
            action_type="thresholds_updated",
            context=new_thresholds
        )


class StreamHealthDashboard:
    """Dashboard for stream processing health visualization."""
    
    def __init__(self, monitor: StreamPerformanceMonitor):
        self.monitor = monitor
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive health summary for dashboard."""
        current_metrics = self.monitor.get_current_metrics()
        if not current_metrics:
            return {"status": "no_data"}
        
        active_alerts = self.monitor.get_active_alerts()
        
        # Determine overall health status
        if any(a.severity == AlertSeverity.CRITICAL for a in active_alerts):
            health_status = "critical"
        elif any(a.severity == AlertSeverity.WARNING for a in active_alerts):
            health_status = "warning"
        else:
            health_status = "healthy"
        
        return {
            "status": health_status,
            "timestamp": current_metrics.timestamp.isoformat(),
            "metrics": {
                "throughput": {
                    "messages_per_second": current_metrics.messages_per_second,
                    "bytes_per_second": current_metrics.bytes_per_second
                },
                "latency": {
                    "avg_ms": current_metrics.avg_processing_latency_ms,
                    "p95_ms": current_metrics.p95_processing_latency_ms,
                    "p99_ms": current_metrics.p99_processing_latency_ms
                },
                "errors": {
                    "error_rate": current_metrics.error_rate,
                    "timeout_rate": current_metrics.timeout_rate,
                    "retry_rate": current_metrics.retry_rate
                },
                "kafka": {
                    "connected": current_metrics.kafka_connection_status,
                    "lag": current_metrics.kafka_lag,
                    "queue_size": current_metrics.producer_queue_size
                },
                "resources": {
                    "cpu_usage": current_metrics.cpu_usage,
                    "memory_usage": current_metrics.memory_usage,
                    "thread_count": current_metrics.thread_count
                }
            },
            "alerts": [
                {
                    "id": alert.alert_id,
                    "severity": alert.severity.value,
                    "title": alert.title,
                    "description": alert.description,
                    "timestamp": alert.timestamp.isoformat()
                }
                for alert in active_alerts
            ]
        }


# Global instances
stream_monitor = StreamPerformanceMonitor()
stream_dashboard = StreamHealthDashboard(stream_monitor)


def default_alert_handler(alert: StreamAlert):
    """Default alert handler for stream processing alerts."""
    # This could integrate with external alerting systems
    pass


# Register default alert handler
stream_monitor.register_alert_callback(default_alert_handler)