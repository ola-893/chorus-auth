"""
Stream analytics engine for real-time system monitoring and analysis.
"""
import time
import math
import logging
from collections import deque, defaultdict
from typing import Dict, Any, List, Optional
from datetime import datetime

from .logging_config import get_agent_logger

agent_logger = get_agent_logger(__name__)
logger = logging.getLogger(__name__)

class MetricsAggregator:
    """
    Aggregates real-time metrics and performs statistical analysis.
    """
    
    def __init__(self, window_size: int = 60):
        """
        Args:
            window_size: Time window in seconds for rolling metrics.
        """
        self.window_size = window_size
        
        # Raw data buffers (timestamp, value)
        self._latencies: deque = deque()
        self._throughput: deque = deque() # timestamp only
        self._errors: deque = deque() # timestamp only
        self._conflicts: deque = deque() # (timestamp, risk_score)
        
        # Resource monitoring
        self._resource_usage: Dict[str, deque] = defaultdict(deque) # resource_type -> (timestamp, amount)
        
        # Agent behavior tracking for anomaly detection
        self._agent_activity: Dict[str, deque] = defaultdict(deque) # agent_id -> (timestamp, request_count)
        
        # Aggregated stats cache
        self._stats_cache: Dict[str, Any] = {}
        self._last_calc_time = 0
        
    def record_latency(self, latency_ms: float):
        """Record processing latency."""
        self._latencies.append((time.time(), latency_ms))
        self._cleanup(self._latencies)

    def record_message(self):
        """Record a processed message (for throughput)."""
        self._throughput.append(time.time())
        self._cleanup(self._throughput)

    def record_error(self):
        """Record an error."""
        self._errors.append(time.time())
        self._cleanup(self._errors)

    def record_conflict(self, risk_score: float):
        """Record a detected conflict."""
        self._conflicts.append((time.time(), risk_score))
        self._cleanup(self._conflicts)

    def record_resource_usage(self, resource_type: str, amount: int):
        """Record resource usage request."""
        self._resource_usage[resource_type].append((time.time(), amount))
        self._cleanup(self._resource_usage[resource_type])

    def record_agent_activity(self, agent_id: str):
        """Record activity for an agent."""
        # We bucket by second or just raw timestamps?
        # Let's just store timestamp
        self._agent_activity[agent_id].append(time.time())
        self._cleanup(self._agent_activity[agent_id])

    def _cleanup(self, buffer: deque):
        """Remove old entries outside window."""
        now = time.time()
        limit = now - self.window_size
        while buffer and (buffer[0] if isinstance(buffer[0], float) else buffer[0][0]) < limit:
            buffer.popleft()

    def calculate_metrics(self) -> Dict[str, Any]:
        """Calculate current metrics."""
        now = time.time()
        # Rate limiting calculation to avoid overhead?
        if now - self._last_calc_time < 0.5:
            return self._stats_cache
            
        # Throughput (msg/sec)
        msg_count = len(self._throughput)
        throughput = msg_count / self.window_size if self.window_size > 0 else 0
        
        # Latency stats
        latencies = [v for t, v in self._latencies]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        max_latency = max(latencies) if latencies else 0
        
        # Error rate
        error_count = len(self._errors)
        error_rate = error_count / msg_count if msg_count > 0 else 0
        
        # Conflict stats
        conflicts = [v for t, v in self._conflicts]
        conflict_rate = len(conflicts) / self.window_size
        avg_risk = sum(conflicts) / len(conflicts) if conflicts else 0
        
        self._stats_cache = {
            "throughput": round(throughput, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "max_latency_ms": round(max_latency, 2),
            "error_rate": round(error_rate, 4),
            "conflict_rate": round(conflict_rate, 2),
            "avg_conflict_risk": round(avg_risk, 3),
            "timestamp": now
        }
        self._last_calc_time = now
        return self._stats_cache

    def detect_anomalies(self) -> List[str]:
        """
        Detect anomalies in system behavior.
        """
        anomalies = []
        stats = self.calculate_metrics()
        
        # 1. Latency Spike
        if stats["avg_latency_ms"] > 500: # Threshold
            anomalies.append(f"High Latency: {stats['avg_latency_ms']}ms")
            
        # 2. Error Rate Spike
        if stats["error_rate"] > 0.05: # 5%
            anomalies.append(f"High Error Rate: {stats['error_rate']*100}%")
            
        # 3. Agent Activity Spikes
        for agent_id, timestamps in self._agent_activity.items():
            # Check rate in last 5 seconds vs window average
            now = time.time()
            recent_count = sum(1 for t in timestamps if t > now - 5)
            # Rate per second
            recent_rate = recent_count / 5.0
            
            # Simple threshold: > 10 req/sec is weird
            if recent_rate > 10:
                anomalies.append(f"Agent Hyperactivity: {agent_id} ({recent_rate} req/s)")
                
        return anomalies

    def identify_bottlenecks(self) -> List[str]:
        """
        Identify resource bottlenecks.
        """
        bottlenecks = []
        for resource, usage in self._resource_usage.items():
            if not usage:
                continue
            total_requested = sum(amount for t, amount in usage)
            # Assuming we know capacity... for now just check total requested vs arbitrary limit or spike
            # Let's say if total requested in window > 10000 units
            if total_requested > 10000:
                bottlenecks.append(f"Resource Constraint: {resource} (Load: {total_requested})")
        return bottlenecks
    
    def get_aggregated_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics including anomalies and bottlenecks.
        """
        metrics = self.calculate_metrics()
        metrics["anomalies"] = self.detect_anomalies()
        metrics["bottlenecks"] = self.identify_bottlenecks()
        return metrics

# Global instance
stream_analytics = MetricsAggregator()
