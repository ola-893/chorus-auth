"""
Alerting integration service that connects Datadog alerting with the trust management system.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .datadog_alerting import datadog_alerting, DatadogAlertingManager
from .datadog_client import datadog_client
from ..prediction_engine.trust_manager import trust_manager
from ..prediction_engine.quarantine_manager import quarantine_manager
from ..system_health import health_monitor
from ..config import settings
from ..event_bus import event_bus

logger = logging.getLogger(__name__)


@dataclass
class AlertingMetrics:
    """Metrics for alerting system performance."""
    alerts_triggered: int = 0
    alerts_resolved: int = 0
    escalations_sent: int = 0
    false_positives: int = 0
    average_resolution_time: float = 0.0


class AlertingIntegrationService:
    """
    Service that integrates Datadog alerting with the Chorus system components.
    
    Monitors system state and automatically triggers/resolves alerts based on
    trust scores, quarantine status, and system health.
    """
    
    def __init__(self, alerting_manager: DatadogAlertingManager = None):
        """
        Initialize the alerting integration service.
        
        Args:
            alerting_manager: Datadog alerting manager instance
        """
        self.alerting_manager = alerting_manager or datadog_alerting
        self.trust_manager = trust_manager
        self.quarantine_manager = quarantine_manager
        self.health_monitor = health_monitor
        
        self.monitoring_active = False
        self.monitoring_task = None
        self.metrics = AlertingMetrics()
        
        # Configuration
        self.monitoring_interval = 30  # seconds
        self.trust_score_threshold = 30
        self.quarantine_threshold = 3
        self.conflict_rate_threshold = 0.7
        
        # State tracking
        self.last_system_state = {}
        self.alert_suppression = {}  # Prevent alert spam
        
        logger.info("Alerting integration service initialized")
    
    async def start_monitoring(self):
        """Start the alerting monitoring service."""
        if self.monitoring_active:
            logger.warning("Alerting monitoring already active")
            return
        
        self.monitoring_active = True
        
        # Set up event listeners
        self._setup_event_listeners()
        
        # Create Datadog monitors
        await self.alerting_manager.create_monitors()
        
        # Start monitoring task
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info("Alerting monitoring service started")
    
    async def stop_monitoring(self):
        """Stop the alerting monitoring service."""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Alerting monitoring service stopped")
    
    def _setup_event_listeners(self):
        """Set up event listeners for system events."""
        # Listen for trust score updates
        event_bus.subscribe("trust_score_update", self._handle_trust_score_update)
        
        # Listen for quarantine events
        event_bus.subscribe("agent_quarantined", self._handle_agent_quarantined)
        event_bus.subscribe("agent_released", self._handle_agent_released)
        
        # Listen for system health events
        event_bus.subscribe("system_health_change", self._handle_system_health_change)
        
        # Listen for conflict prediction events
        event_bus.subscribe("conflict_predicted", self._handle_conflict_predicted)
        
        logger.info("Event listeners set up for alerting integration")
    
    async def _monitoring_loop(self):
        """Main monitoring loop that checks system state and processes alerts."""
        while self.monitoring_active:
            try:
                # Collect current system state
                current_state = await self._collect_system_state()
                
                # Process automatic alert resolution
                await self.alerting_manager.process_auto_resolution(current_state)
                
                # Check for new alert conditions
                await self._check_alert_conditions(current_state)
                
                # Update metrics
                await self._update_metrics()
                
                # Store current state for next iteration
                self.last_system_state = current_state
                
                # Wait for next monitoring cycle
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in alerting monitoring loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retrying
    
    async def _collect_system_state(self) -> Dict[str, Any]:
        """
        Collect current system state for alert processing.
        
        Returns:
            Dictionary containing current system state
        """
        try:
            # Get trust scores for all agents
            agent_trust_scores = {}
            quarantined_agents = self.quarantine_manager.get_quarantined_agents()
            
            # Get trust scores for active agents
            active_agents = self.quarantine_manager.get_active_agents()
            for agent_id in active_agents:
                try:
                    score = self.trust_manager.get_trust_score(agent_id)
                    agent_trust_scores[agent_id] = score
                except Exception as e:
                    logger.warning(f"Failed to get trust score for agent {agent_id}: {e}")
            
            # Get system health status
            component_health = {}
            try:
                health_status = self.health_monitor.get_health_status()
                for component, status in health_status.items():
                    component_health[component] = status.get("status", "unknown")
            except Exception as e:
                logger.warning(f"Failed to get system health status: {e}")
            
            # Calculate conflict rate (mock for now - would come from prediction engine)
            conflict_rate = 0.0  # This would be calculated from recent conflict predictions
            
            return {
                "timestamp": datetime.now(),
                "agent_trust_scores": agent_trust_scores,
                "quarantined_count": len(quarantined_agents),
                "quarantined_agents": quarantined_agents,
                "active_agent_count": len(active_agents),
                "component_health": component_health,
                "conflict_rate": conflict_rate,
                "low_trust_agents": [
                    agent_id for agent_id, score in agent_trust_scores.items()
                    if score < self.trust_score_threshold
                ]
            }
            
        except Exception as e:
            logger.error(f"Error collecting system state: {e}")
            return {"timestamp": datetime.now(), "error": str(e)}
    
    async def _check_alert_conditions(self, current_state: Dict[str, Any]):
        """
        Check for alert conditions in current system state.
        
        Args:
            current_state: Current system state
        """
        try:
            # Check trust score alerts
            await self._check_trust_score_alerts(current_state)
            
            # Check quarantine alerts
            await self._check_quarantine_alerts(current_state)
            
            # Check system health alerts
            await self._check_system_health_alerts(current_state)
            
            # Check conflict rate alerts
            await self._check_conflict_rate_alerts(current_state)
            
        except Exception as e:
            logger.error(f"Error checking alert conditions: {e}")
    
    async def _check_trust_score_alerts(self, current_state: Dict[str, Any]):
        """Check for trust score alert conditions."""
        agent_trust_scores = current_state.get("agent_trust_scores", {})
        
        for agent_id, trust_score in agent_trust_scores.items():
            if trust_score < self.trust_score_threshold:
                # Check if we should suppress this alert (prevent spam)
                if self._should_suppress_alert("trust_score", agent_id):
                    continue
                
                alert_id = self.alerting_manager.check_trust_score_alert(agent_id, trust_score)
                if alert_id:
                    self.metrics.alerts_triggered += 1
                    self._record_alert_suppression("trust_score", agent_id)
                    
                    # Send to Datadog
                    datadog_client.send_metric(
                        "chorus.alert.triggered",
                        1.0,
                        tags=[f"alert_type:trust_score", f"agent_id:{agent_id}"],
                        metric_type="count"
                    )
    
    async def _check_quarantine_alerts(self, current_state: Dict[str, Any]):
        """Check for quarantine alert conditions."""
        quarantined_count = current_state.get("quarantined_count", 0)
        
        if quarantined_count > self.quarantine_threshold:
            # Check if we should suppress this alert
            if self._should_suppress_alert("quarantine", "system"):
                return
            
            alert_id = self.alerting_manager.check_multiple_quarantines_alert(
                quarantined_count, self.quarantine_threshold
            )
            if alert_id:
                self.metrics.alerts_triggered += 1
                self.metrics.escalations_sent += 1  # Multiple quarantines always escalate
                self._record_alert_suppression("quarantine", "system")
                
                # Send to Datadog
                datadog_client.send_metric(
                    "chorus.alert.triggered",
                    1.0,
                    tags=[f"alert_type:multiple_quarantines", f"count:{quarantined_count}"],
                    metric_type="count"
                )
    
    async def _check_system_health_alerts(self, current_state: Dict[str, Any]):
        """Check for system health alert conditions."""
        component_health = current_state.get("component_health", {})
        
        for component, status in component_health.items():
            if status not in ["healthy", "ok"]:
                # Check if we should suppress this alert
                if self._should_suppress_alert("system_health", component):
                    continue
                
                alert_id = self.alerting_manager.check_system_health_alert(component, status)
                if alert_id:
                    self.metrics.alerts_triggered += 1
                    self._record_alert_suppression("system_health", component)
                    
                    # Send to Datadog
                    datadog_client.send_metric(
                        "chorus.alert.triggered",
                        1.0,
                        tags=[f"alert_type:system_health", f"component:{component}"],
                        metric_type="count"
                    )
    
    async def _check_conflict_rate_alerts(self, current_state: Dict[str, Any]):
        """Check for conflict rate alert conditions."""
        conflict_rate = current_state.get("conflict_rate", 0.0)
        
        if conflict_rate > self.conflict_rate_threshold:
            # Check if we should suppress this alert
            if self._should_suppress_alert("conflict_rate", "system"):
                return
            
            alert_id = self.alerting_manager.check_conflict_rate_alert(
                conflict_rate, self.conflict_rate_threshold
            )
            if alert_id:
                self.metrics.alerts_triggered += 1
                self._record_alert_suppression("conflict_rate", "system")
                
                # Send to Datadog
                datadog_client.send_metric(
                    "chorus.alert.triggered",
                    1.0,
                    tags=[f"alert_type:conflict_rate", f"rate:{conflict_rate}"],
                    metric_type="count"
                )
    
    def _should_suppress_alert(self, alert_type: str, identifier: str) -> bool:
        """
        Check if an alert should be suppressed to prevent spam.
        
        Args:
            alert_type: Type of alert
            identifier: Unique identifier for the alert
            
        Returns:
            True if alert should be suppressed
        """
        suppression_key = f"{alert_type}:{identifier}"
        
        if suppression_key in self.alert_suppression:
            last_alert_time = self.alert_suppression[suppression_key]
            # Suppress alerts for 5 minutes after last alert
            if (datetime.now() - last_alert_time).total_seconds() < 300:
                return True
        
        return False
    
    def _record_alert_suppression(self, alert_type: str, identifier: str):
        """Record alert suppression timestamp."""
        suppression_key = f"{alert_type}:{identifier}"
        self.alert_suppression[suppression_key] = datetime.now()
    
    async def _update_metrics(self):
        """Update alerting metrics."""
        try:
            # Get alert statistics from alerting manager
            alert_stats = self.alerting_manager.get_alert_statistics()
            
            # Send metrics to Datadog
            datadog_client.send_metric(
                "chorus.alerting.active_alerts",
                float(alert_stats.get("total_active", 0)),
                metric_type="gauge"
            )
            
            datadog_client.send_metric(
                "chorus.alerting.resolved_alerts",
                float(alert_stats.get("total_resolved", 0)),
                metric_type="gauge"
            )
            
            datadog_client.send_metric(
                "chorus.alerting.escalations_sent",
                float(self.metrics.escalations_sent),
                metric_type="count"
            )
            
        except Exception as e:
            logger.error(f"Error updating alerting metrics: {e}")
    
    # Event handlers
    
    def _handle_trust_score_update(self, event_data: Dict[str, Any]):
        """Handle trust score update events."""
        try:
            agent_id = event_data.get("agent_id")
            new_score = event_data.get("new_score")
            old_score = event_data.get("old_score")
            
            if agent_id and new_score is not None and old_score is not None:
                # Check if this is a recovery (score improved significantly)
                if old_score < self.trust_score_threshold and new_score >= self.trust_score_threshold + 5:
                    # Look for active trust score alerts for this agent
                    for alert_id, alert_data in self.alerting_manager.active_alerts.items():
                        if (alert_data.get("type") == "trust_score_low" and 
                            alert_data.get("agent_id") == agent_id):
                            
                            # Trigger automatic resolution
                            self.alerting_manager.resolve_alert_automatically(
                                alert_id, f"trust_score_recovered_to_{new_score}"
                            )
                            
                            logger.info(f"Auto-resolved trust score alert for agent {agent_id}")
                            break
                            
        except Exception as e:
            logger.error(f"Error handling trust score update event: {e}")
    
    def _handle_agent_quarantined(self, event_data: Dict[str, Any]):
        """Handle agent quarantined events."""
        try:
            agent_id = event_data.get("agent_id")
            reason = event_data.get("reason", "unknown")
            
            logger.info(f"Agent {agent_id} quarantined: {reason}")
            
            # This will be picked up by the monitoring loop for quarantine count alerts
            
        except Exception as e:
            logger.error(f"Error handling agent quarantined event: {e}")
    
    def _handle_agent_released(self, event_data: Dict[str, Any]):
        """Handle agent released events."""
        try:
            agent_id = event_data.get("agent_id")
            
            logger.info(f"Agent {agent_id} released from quarantine")
            
            # This will be picked up by the monitoring loop for resolution checking
            
        except Exception as e:
            logger.error(f"Error handling agent released event: {e}")
    
    def _handle_system_health_change(self, event_data: Dict[str, Any]):
        """Handle system health change events."""
        try:
            component = event_data.get("component")
            old_status = event_data.get("old_status")
            new_status = event_data.get("new_status")
            
            if component and new_status:
                # Check if this is a recovery
                if old_status in ["unhealthy", "degraded", "failed"] and new_status == "healthy":
                    # Look for active system health alerts for this component
                    for alert_id, alert_data in self.alerting_manager.active_alerts.items():
                        if (alert_data.get("type") == "system_health" and 
                            alert_data.get("component") == component):
                            
                            # Trigger automatic resolution
                            self.alerting_manager.resolve_alert_automatically(
                                alert_id, f"component_{component}_recovered"
                            )
                            
                            logger.info(f"Auto-resolved system health alert for component {component}")
                            break
                            
        except Exception as e:
            logger.error(f"Error handling system health change event: {e}")
    
    def _handle_conflict_predicted(self, event_data: Dict[str, Any]):
        """Handle conflict predicted events."""
        try:
            risk_score = event_data.get("risk_score", 0.0)
            affected_agents = event_data.get("affected_agents", [])
            
            # Update conflict rate tracking (simplified)
            # In a real implementation, this would maintain a rolling window
            if risk_score > self.conflict_rate_threshold:
                logger.info(f"High-risk conflict predicted: {risk_score} affecting {len(affected_agents)} agents")
            
        except Exception as e:
            logger.error(f"Error handling conflict predicted event: {e}")
    
    async def test_end_to_end_alerting(self) -> Dict[str, Any]:
        """
        Test end-to-end alerting workflow.
        
        Returns:
            Test results dictionary
        """
        test_results = {
            "monitor_creation": False,
            "alert_triggering": False,
            "escalation": False,
            "resolution": False,
            "notifications": False,
            "errors": []
        }
        
        try:
            logger.info("Starting end-to-end alerting test")
            
            # Test 1: Monitor creation
            try:
                created_monitors = await self.alerting_manager.create_monitors()
                test_results["monitor_creation"] = len(created_monitors) > 0
                logger.info(f"Monitor creation test: {'PASS' if test_results['monitor_creation'] else 'FAIL'}")
            except Exception as e:
                test_results["errors"].append(f"Monitor creation failed: {e}")
            
            # Test 2: Alert triggering
            try:
                # Simulate low trust score alert
                test_agent_id = "test_agent_001"
                alert_id = self.alerting_manager.check_trust_score_alert(test_agent_id, 15.0)
                test_results["alert_triggering"] = alert_id is not None
                logger.info(f"Alert triggering test: {'PASS' if test_results['alert_triggering'] else 'FAIL'}")
                
                # Test 3: Escalation
                if alert_id:
                    # Simulate multiple quarantines for escalation test
                    escalation_alert_id = self.alerting_manager.check_multiple_quarantines_alert(5, 3)
                    test_results["escalation"] = escalation_alert_id is not None
                    logger.info(f"Escalation test: {'PASS' if test_results['escalation'] else 'FAIL'}")
                    
                    # Test 4: Resolution
                    self.alerting_manager.resolve_alert_automatically(alert_id, "test_resolution")
                    test_results["resolution"] = self.alerting_manager.is_alert_resolved(alert_id)
                    logger.info(f"Resolution test: {'PASS' if test_results['resolution'] else 'FAIL'}")
                    
                    # Test 5: Notifications
                    try:
                        await self.alerting_manager.send_recovery_notification(
                            alert_id, "trust_score_low", {"test": True}
                        )
                        test_results["notifications"] = True
                        logger.info("Notification test: PASS")
                    except Exception as e:
                        test_results["errors"].append(f"Notification test failed: {e}")
                        logger.info("Notification test: FAIL")
                        
            except Exception as e:
                test_results["errors"].append(f"Alert workflow test failed: {e}")
            
            # Calculate overall success
            test_results["overall_success"] = (
                test_results["monitor_creation"] and
                test_results["alert_triggering"] and
                test_results["escalation"] and
                test_results["resolution"] and
                test_results["notifications"]
            )
            
            logger.info(f"End-to-end alerting test completed: {'PASS' if test_results['overall_success'] else 'FAIL'}")
            
        except Exception as e:
            test_results["errors"].append(f"Test framework error: {e}")
            logger.error(f"End-to-end alerting test failed: {e}")
        
        return test_results
    
    def get_metrics(self) -> AlertingMetrics:
        """Get current alerting metrics."""
        return self.metrics
    
    def get_status(self) -> Dict[str, Any]:
        """Get current alerting service status."""
        return {
            "monitoring_active": self.monitoring_active,
            "alerting_enabled": self.alerting_manager.enabled,
            "active_alerts": len(self.alerting_manager.active_alerts),
            "resolved_alerts": len(self.alerting_manager.resolved_alerts),
            "metrics": {
                "alerts_triggered": self.metrics.alerts_triggered,
                "alerts_resolved": self.metrics.alerts_resolved,
                "escalations_sent": self.metrics.escalations_sent
            }
        }


# Global instance
alerting_integration = AlertingIntegrationService()