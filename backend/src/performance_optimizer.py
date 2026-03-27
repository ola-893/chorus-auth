"""
Performance optimization utilities for production readiness.
"""
import os
import time
import threading
import psutil
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config import settings
from .logging_config import get_agent_logger
from .integrations.kafka_client import kafka_bus
from .stream_analytics import stream_analytics

agent_logger = get_agent_logger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for system optimization."""
    cpu_usage: float
    memory_usage: float
    disk_io: Dict[str, float]
    network_io: Dict[str, float]
    kafka_throughput: float
    kafka_latency: float
    redis_latency: float
    gemini_latency: float
    timestamp: float


class KafkaOptimizer:
    """Optimizes Kafka configurations for production workloads."""
    
    def __init__(self):
        self.optimized_producer_config = {}
        self.optimized_consumer_config = {}
        self._setup_production_configs()
    
    def _setup_production_configs(self):
        """Setup optimized Kafka configurations for production."""
        
        # Production-optimized Producer configuration
        self.optimized_producer_config = {
            # Performance optimizations
            'compression.type': 'lz4',  # Better compression ratio than snappy
            'linger.ms': 5,  # Reduced from 10ms for lower latency
            'batch.size': 65536,  # Increased from 32KB for better throughput
            'buffer.memory': 67108864,  # 64MB buffer
            'max.in.flight.requests.per.connection': 5,
            
            # Reliability optimizations
            'acks': 'all',  # Wait for all replicas
            'retries': 10,  # Increased retries
            'retry.backoff.ms': 100,
            'delivery.timeout.ms': 120000,  # 2 minutes
            'request.timeout.ms': 30000,
            
            # Connection optimizations
            'connections.max.idle.ms': 540000,  # 9 minutes
            'reconnect.backoff.ms': 50,
            'reconnect.backoff.max.ms': 1000,
            
            # Monitoring
            'enable.idempotence': True,
            'client.id': f'chorus-producer-{os.getpid()}',
        }
        
        # Production-optimized Consumer configuration
        self.optimized_consumer_config = {
            # Performance optimizations
            'fetch.min.bytes': 50000,  # Increased from 1KB
            'fetch.max.wait.ms': 500,
            'max.partition.fetch.bytes': 2097152,  # 2MB
            'receive.buffer.bytes': 262144,  # 256KB
            'send.buffer.bytes': 131072,  # 128KB
            
            # Reliability optimizations
            'session.timeout.ms': 30000,  # Reduced from 45s
            'heartbeat.interval.ms': 3000,
            'max.poll.interval.ms': 300000,  # 5 minutes
            'max.poll.records': 1000,  # Increased batch size
            
            # Connection optimizations
            'connections.max.idle.ms': 540000,
            'reconnect.backoff.ms': 50,
            'reconnect.backoff.max.ms': 1000,
            
            # Offset management
            'enable.auto.commit': False,  # Manual commits for reliability
            'auto.offset.reset': 'earliest',
            
            # Monitoring
            'client.id': f'chorus-consumer-{os.getpid()}',
        }
    
    def get_optimized_producer_config(self) -> Dict[str, Any]:
        """Get optimized producer configuration."""
        base_config = settings.get_kafka_config()
        base_config.update(self.optimized_producer_config)
        return base_config
    
    def get_optimized_consumer_config(self, group_id: str) -> Dict[str, Any]:
        """Get optimized consumer configuration."""
        base_config = settings.get_kafka_config()
        base_config.update(self.optimized_consumer_config)
        base_config['group.id'] = group_id
        return base_config
    
    def validate_confluent_cloud_config(self) -> List[str]:
        """Validate Confluent Cloud specific configuration."""
        issues = []
        
        if not settings.kafka.enabled:
            return issues
        
        # Check for Confluent Cloud bootstrap servers
        if 'confluent.cloud' in settings.kafka.bootstrap_servers:
            # Validate SASL_SSL configuration
            if settings.kafka.security_protocol != 'SASL_SSL':
                issues.append("Confluent Cloud requires SASL_SSL security protocol")
            
            if settings.kafka.sasl_mechanism != 'PLAIN':
                issues.append("Confluent Cloud requires PLAIN SASL mechanism")
            
            if not settings.kafka.sasl_username or not settings.kafka.sasl_password:
                issues.append("Confluent Cloud requires SASL username and password")
            
            # Validate API key format (basic check)
            if settings.kafka.sasl_username and len(settings.kafka.sasl_username) < 10:
                issues.append("Confluent Cloud API key appears to be invalid (too short)")
        
        # Check topic naming conventions
        topics = [
            settings.kafka.agent_messages_topic,
            settings.kafka.agent_decisions_topic,
            settings.kafka.system_alerts_topic,
            settings.kafka.causal_graph_updates_topic,
            settings.kafka.analytics_metrics_topic
        ]
        
        for topic in topics:
            if not topic or len(topic) < 3:
                issues.append(f"Topic name '{topic}' is too short")
            if ' ' in topic:
                issues.append(f"Topic name '{topic}' contains spaces")
        
        return issues


class ConnectionPoolManager:
    """Manages connection pools for various services."""
    
    def __init__(self):
        self.redis_pool = None
        self.kafka_producer_pool = None
        self.thread_pool = ThreadPoolExecutor(
            max_workers=min(32, (os.cpu_count() or 1) + 4),
            thread_name_prefix="chorus-worker"
        )
        self._setup_pools()
    
    def _setup_pools(self):
        """Setup connection pools for services."""
        try:
            # Redis connection pool is already handled in redis_client.py
            # Kafka connection pooling is handled by the client library
            agent_logger.log_agent_action(
                "INFO",
                "Connection pools initialized",
                action_type="connection_pools_init",
                context={"thread_pool_workers": self.thread_pool._max_workers}
            )
        except Exception as e:
            agent_logger.log_system_error(e, "connection_pool_manager", "setup_pools")
    
    def get_thread_pool(self) -> ThreadPoolExecutor:
        """Get the shared thread pool."""
        return self.thread_pool
    
    def shutdown(self):
        """Shutdown connection pools."""
        if self.thread_pool:
            self.thread_pool.shutdown(wait=True)


class PerformanceMonitor:
    """Monitors system performance and provides optimization recommendations."""
    
    def __init__(self):
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.metrics_history: List[PerformanceMetrics] = []
        self.max_history = 300  # 5 minutes at 1-second intervals
        
    def start_monitoring(self):
        """Start performance monitoring."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        agent_logger.log_agent_action(
            "INFO",
            "Performance monitoring started",
            action_type="performance_monitor_start"
        )
    
    def stop_monitoring(self):
        """Stop performance monitoring."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
    
    def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring:
            try:
                metrics = self._collect_metrics()
                self.metrics_history.append(metrics)
                
                # Keep history size manageable
                if len(self.metrics_history) > self.max_history:
                    self.metrics_history.pop(0)
                
                # Check for performance issues
                self._check_performance_alerts(metrics)
                
                time.sleep(1.0)
                
            except Exception as e:
                agent_logger.log_system_error(e, "performance_monitor", "monitoring_loop")
                time.sleep(5.0)
    
    def _collect_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics."""
        try:
            # System metrics
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk_io = psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {}
            network_io = psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {}
            
            # Stream analytics metrics
            stream_metrics = stream_analytics.calculate_metrics()
            
            return PerformanceMetrics(
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                disk_io=disk_io,
                network_io=network_io,
                kafka_throughput=stream_metrics.get('throughput', 0),
                kafka_latency=stream_metrics.get('avg_latency_ms', 0),
                redis_latency=0,  # Would need to implement Redis latency tracking
                gemini_latency=0,  # Would need to implement Gemini latency tracking
                timestamp=time.time()
            )
            
        except Exception as e:
            agent_logger.log_system_error(e, "performance_monitor", "collect_metrics")
            return PerformanceMetrics(0, 0, {}, {}, 0, 0, 0, 0, time.time())
    
    def _check_performance_alerts(self, metrics: PerformanceMetrics):
        """Check for performance issues and generate alerts."""
        alerts = []
        
        # CPU usage alerts
        if metrics.cpu_usage > 90:
            alerts.append(f"High CPU usage: {metrics.cpu_usage:.1f}%")
        
        # Memory usage alerts
        if metrics.memory_usage > 85:
            alerts.append(f"High memory usage: {metrics.memory_usage:.1f}%")
        
        # Kafka performance alerts
        if metrics.kafka_latency > 1000:  # 1 second
            alerts.append(f"High Kafka latency: {metrics.kafka_latency:.1f}ms")
        
        if metrics.kafka_throughput < 1 and len(self.metrics_history) > 30:
            # Check if throughput has been consistently low
            recent_throughput = [m.kafka_throughput for m in self.metrics_history[-30:]]
            avg_throughput = sum(recent_throughput) / len(recent_throughput)
            if avg_throughput < 1:
                alerts.append(f"Low Kafka throughput: {avg_throughput:.2f} msg/s")
        
        # Log alerts
        for alert in alerts:
            agent_logger.log_agent_action(
                "WARNING",
                f"Performance alert: {alert}",
                action_type="performance_alert",
                context={"metric_type": alert.split(':')[0]}
            )
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary and recommendations."""
        if not self.metrics_history:
            return {"status": "no_data"}
        
        recent_metrics = self.metrics_history[-10:]  # Last 10 seconds
        
        avg_cpu = sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)
        avg_kafka_latency = sum(m.kafka_latency for m in recent_metrics) / len(recent_metrics)
        avg_kafka_throughput = sum(m.kafka_throughput for m in recent_metrics) / len(recent_metrics)
        
        recommendations = []
        
        # Generate recommendations
        if avg_cpu > 80:
            recommendations.append("Consider scaling horizontally or optimizing CPU-intensive operations")
        
        if avg_memory > 80:
            recommendations.append("Consider increasing memory allocation or optimizing memory usage")
        
        if avg_kafka_latency > 500:
            recommendations.append("Consider optimizing Kafka configuration or network connectivity")
        
        if avg_kafka_throughput < 10:
            recommendations.append("Consider increasing Kafka batch sizes or connection pooling")
        
        return {
            "status": "healthy" if not recommendations else "needs_attention",
            "metrics": {
                "avg_cpu_usage": round(avg_cpu, 2),
                "avg_memory_usage": round(avg_memory, 2),
                "avg_kafka_latency": round(avg_kafka_latency, 2),
                "avg_kafka_throughput": round(avg_kafka_throughput, 2)
            },
            "recommendations": recommendations,
            "data_points": len(self.metrics_history)
        }


class ResourceManager:
    """Manages system resources and implements resource optimization strategies."""
    
    def __init__(self):
        self.resource_limits = {
            'max_memory_usage': 85.0,  # Percentage
            'max_cpu_usage': 90.0,     # Percentage
            'max_open_files': 1000,
            'max_threads': 100
        }
        
    def check_resource_constraints(self) -> Dict[str, Any]:
        """Check current resource usage against limits."""
        try:
            # Memory check
            memory = psutil.virtual_memory()
            memory_ok = memory.percent < self.resource_limits['max_memory_usage']
            
            # CPU check
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_ok = cpu_percent < self.resource_limits['max_cpu_usage']
            
            # Process-specific checks
            process = psutil.Process()
            open_files = len(process.open_files()) if hasattr(process, 'open_files') else 0
            files_ok = open_files < self.resource_limits['max_open_files']
            
            threads = process.num_threads()
            threads_ok = threads < self.resource_limits['max_threads']
            
            return {
                'memory': {'usage': memory.percent, 'ok': memory_ok},
                'cpu': {'usage': cpu_percent, 'ok': cpu_ok},
                'open_files': {'count': open_files, 'ok': files_ok},
                'threads': {'count': threads, 'ok': threads_ok},
                'overall_ok': all([memory_ok, cpu_ok, files_ok, threads_ok])
            }
            
        except Exception as e:
            agent_logger.log_system_error(e, "resource_manager", "check_constraints")
            return {'overall_ok': False, 'error': str(e)}
    
    def optimize_garbage_collection(self):
        """Trigger garbage collection and memory optimization."""
        import gc
        
        before_count = len(gc.get_objects())
        collected = gc.collect()
        after_count = len(gc.get_objects())
        
        agent_logger.log_agent_action(
            "INFO",
            f"Garbage collection completed: {collected} objects collected, {before_count - after_count} objects freed",
            action_type="gc_optimization"
        )


# Global instances
kafka_optimizer = KafkaOptimizer()
connection_pool_manager = ConnectionPoolManager()
performance_monitor = PerformanceMonitor()
resource_manager = ResourceManager()