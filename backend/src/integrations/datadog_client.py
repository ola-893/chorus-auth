"""
Datadog integration client for metrics and logging.
"""
from typing import Dict, Any, Optional, List
import time
from datetime import datetime
import json
import logging

try:
    from datadog_api_client import ApiClient, Configuration
    from datadog_api_client.v2.api.logs_api import LogsApi
    from datadog_api_client.v2.model.http_log import HTTPLog
    from datadog_api_client.v2.model.http_log_item import HTTPLogItem
    from datadog_api_client.v1.api.metrics_api import MetricsApi
    from datadog_api_client.v1.model.metrics_payload import MetricsPayload
    from datadog_api_client.v1.model.series import Series
    from datadog_api_client.v1.model.point import Point
    from datadog_api_client.v1.api.events_api import EventsApi
    from datadog_api_client.v1.model.event_create_request import EventCreateRequest
except ImportError:
    ApiClient = None
    Configuration = None
    LogsApi = None
    HTTPLog = None
    HTTPLogItem = None
    MetricsApi = None
    MetricsPayload = None
    Series = None
    Point = None
    EventsApi = None
    EventCreateRequest = None

import socket
import threading
from collections import deque
from ..config import settings
from ..error_handling import CircuitBreaker, SystemRecoveryError

logger = logging.getLogger(__name__)

# Circuit breaker for Datadog API calls
datadog_circuit_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=30.0,
    expected_exception=Exception
)

class DatadogClient:
    """
    Client for interacting with Datadog API for metrics and logs.
    """
    
    def __init__(self):
        """Initialize Datadog client."""
        self.enabled = settings.datadog.enabled
        self.api_key = settings.datadog.api_key
        self.app_key = settings.datadog.app_key
        self.site = settings.datadog.site
        
        self.api_client = None
        self.logs_api = None
        self.metrics_api = None
        
        # Buffering
        self.metric_buffer = deque(maxlen=1000)
        self.log_buffer = deque(maxlen=1000)
        self.flush_interval = 5.0
        self.running = False
        self.flush_thread = None
        
        if self.enabled and self.api_key and self.app_key:
            self._initialize_client()
            self._start_flush_thread()
    
    def _initialize_client(self):
        """Initialize the Datadog API client."""
        if not ApiClient:
            logger.warning("datadog-api-client not installed. Datadog integration disabled.")
            self.enabled = False
            return

        try:
            configuration = Configuration()
            configuration.api_key["apiKeyAuth"] = self.api_key
            configuration.api_key["appKeyAuth"] = self.app_key
            configuration.server_variables["site"] = self.site
            
            self.api_client = ApiClient(configuration)
            self.logs_api = LogsApi(self.api_client)
            self.metrics_api = MetricsApi(self.api_client)
            if EventsApi:
                self.events_api = EventsApi(self.api_client)
            else:
                logger.warning("Datadog EventsApi not available")
            
            logger.info("Datadog client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Datadog client: {e}")
            self.enabled = False

    def _start_flush_thread(self):
        """Start background thread for flushing buffers."""
        self.running = True
        self.flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self.flush_thread.start()

    def _flush_loop(self):
        """Background loop to flush buffers periodically."""
        while self.running:
            try:
                time.sleep(self.flush_interval)
                self._flush_buffers()
            except Exception as e:
                # Don't let flush errors kill the thread
                logger.debug(f"Error in Datadog flush loop: {e}")

    def _flush_buffers(self):
        """Flush pending metrics and logs."""
        # Flush metrics
        while self.metric_buffer:
            try:
                # Peek first
                metric_data = self.metric_buffer[0]
                self._send_metric_direct(
                    metric_data['name'], 
                    metric_data['value'], 
                    metric_data.get('tags'), 
                    metric_data.get('metric_type')
                )
                # Pop if successful
                self.metric_buffer.popleft()
            except Exception:
                # Stop flushing on error to preserve order/data
                break

        # Flush logs
        while self.log_buffer:
            try:
                log_data = self.log_buffer[0]
                self._send_log_direct(
                    log_data['message'],
                    log_data.get('level'),
                    log_data.get('context'),
                    log_data.get('source')
                )
                self.log_buffer.popleft()
            except Exception:
                break

    def stop(self):
        """Stop the client and flush remaining buffers."""
        self.running = False
        if self.flush_thread:
            self.flush_thread.join(timeout=2.0)
        self._flush_buffers()

    @datadog_circuit_breaker
    def create_event(self, title: str, text: str, alert_type: str = "info", tags: Optional[List[str]] = None):
        """Create a Datadog event."""
        if not self.enabled or not self.events_api:
            return

        try:
            body = EventCreateRequest(
                title=title,
                text=text,
                alert_type=alert_type,
                tags=tags or [f"env:{settings.environment.value}"],
                source_type_name="chorus-backend"
            )
            self.events_api.create_event(body)
            logger.info(f"Datadog event created: {title}")
        except Exception as e:
            logger.error(f"Failed to create Datadog event: {e}")

    def send_log(self, message: str, level: str = "INFO", context: Optional[Dict[str, Any]] = None, source: str = "chorus-backend"):
        """Queue a log for sending."""
        if not self.enabled:
            return

        self.log_buffer.append({
            "message": message,
            "level": level,
            "context": context,
            "source": source
        })

    @datadog_circuit_breaker
    def _send_log_direct(self, message: str, level: str = "INFO", context: Optional[Dict[str, Any]] = None, source: str = "chorus-backend"):
        """
        Internal method to send log immediately.
        """
        if not self.enabled or not self.logs_api:
            return

        try:
            body = HTTPLog(
                [
                    HTTPLogItem(
                        message=message,
                        ddsource=source,
                        ddtags=f"env:{settings.environment.value}",
                        service="chorus-conflict-predictor",
                        status=level,
                        additional_properties=context or {},
                        hostname=socket.gethostname()
                    )
                ]
            )
            
            self.logs_api.submit_log(body)
            
        except Exception as e:
            # Don't crash app on logging failure, just log to local stderr
            logger.error(f"Failed to send log to Datadog: {e}")
            raise  # Let circuit breaker handle the failure

    def send_metric(self, metric_name: str, value: float, tags: Optional[List[str]] = None, metric_type: str = "gauge"):
        """Queue a metric for sending."""
        if not self.enabled:
            return

        self.metric_buffer.append({
            "name": metric_name, 
            "value": value, 
            "tags": tags, 
            "metric_type": metric_type
        })

    @datadog_circuit_breaker
    def _send_metric_direct(self, metric_name: str, value: float, tags: Optional[List[str]] = None, metric_type: str = "gauge"):
        """
        Internal method to send metric immediately.
        """
        if not self.enabled or not self.metrics_api:
            return

        try:
            current_tags = [f"env:{settings.environment.value}"]
            if tags:
                current_tags.extend(tags)
            
            body = MetricsPayload(
                series=[
                    Series(
                        metric=metric_name,
                        points=[Point([datetime.now().timestamp(), value])],
                        tags=current_tags,
                        type=metric_type,
                    )
                ]
            )
            
            self.metrics_api.submit_metrics(body)
            
        except Exception as e:
            logger.error(f"Failed to send metric to Datadog: {e}")
            raise  # Let circuit breaker handle the failure

    def track_trust_score_change(self, agent_id: str, old_score: int, new_score: int, reason: str):
        """
        Track agent trust score changes.
        """
        try:
            self.send_metric(
                "chorus.agent.trust_score",
                float(new_score),
                tags=[f"agent_id:{agent_id}"],
                metric_type="gauge"
            )
        except SystemRecoveryError:
            # Circuit breaker is open, gracefully degrade
            logger.debug(f"Datadog circuit breaker open, skipping trust score metric for {agent_id}")
        
        try:
            self.send_log(
                f"Trust score changed for agent {agent_id}: {old_score} -> {new_score}",
                level="INFO",
                context={
                    "agent_id": agent_id,
                    "old_score": old_score,
                    "new_score": new_score,
                    "reason": reason,
                    "change": new_score - old_score
                }
            )
        except SystemRecoveryError:
            # Circuit breaker is open, gracefully degrade
            logger.debug(f"Datadog circuit breaker open, skipping trust score log for {agent_id}")

    def track_conflict_prediction(self, conflict_id: str, risk_score: float, affected_agents: List[str]):
        """
        Track conflict predictions.
        """
        try:
            self.send_metric(
                "chorus.conflict.risk_score",
                risk_score,
                tags=[f"conflict_id:{conflict_id}"],
                metric_type="gauge"
            )
        except SystemRecoveryError:
            # Circuit breaker is open, gracefully degrade
            logger.debug(f"Datadog circuit breaker open, skipping conflict prediction metric for {conflict_id}")
        
        try:
            self.send_log(
                f"Conflict predicted with risk score {risk_score}",
                level="WARN" if risk_score > settings.conflict_prediction.risk_threshold else "INFO",
                context={
                    "conflict_id": conflict_id,
                    "risk_score": risk_score,
                    "affected_agents": affected_agents
                }
            )
        except SystemRecoveryError:
            # Circuit breaker is open, gracefully degrade
            logger.debug(f"Datadog circuit breaker open, skipping conflict prediction log for {conflict_id}")

    def track_llm_usage(self, model: str, prompt_tokens: int, completion_tokens: int, latency_ms: float, finish_reason: str):
        """
        Track LLM usage metrics (Tokens, Latency).
        """
        try:
            tags = [f"model:{model}", f"finish_reason:{finish_reason}"]
            
            # Track Latency
            self.send_metric(
                "chorus.gemini.latency",
                latency_ms,
                tags=tags,
                metric_type="gauge"
            )

            # Track Tokens
            self.send_metric(
                "chorus.gemini.tokens.prompt",
                float(prompt_tokens),
                tags=tags,
                metric_type="count"
            )
            self.send_metric(
                "chorus.gemini.tokens.completion",
                float(completion_tokens),
                tags=tags,
                metric_type="count"
            )
            self.send_metric(
                "chorus.gemini.tokens.total",
                float(prompt_tokens + completion_tokens),
                tags=tags,
                metric_type="count"
            )

            # Track Request Count
            self.send_metric(
                "chorus.gemini.request",
                1.0,
                tags=tags,
                metric_type="count"
            )

        except SystemRecoveryError:
             logger.debug("Datadog circuit breaker open, skipping LLM usage metrics")
        except Exception as e:
            logger.error(f"Failed to track LLM usage: {e}")

# Global instance
datadog_client = DatadogClient()
