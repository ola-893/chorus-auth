
import pytest
from unittest.mock import MagicMock, patch
from src.system_health import SystemHealthMonitor, HealthStatus

class TestPropertyHealthMonitoring:
    """
    Property 1: Comprehensive health monitoring reliability.
    """

    def test_health_check_registration(self):
        """Verify all critical integrations have health checks registered."""
        monitor = SystemHealthMonitor()
        
        # Check if all expected checks are present
        expected_checks = [
            "redis_connection", 
            "gemini_api", 
            "datadog_api", 
            "kafka_connection", 
            "elevenlabs_api", 
            "system_resources"
        ]
        
        for check_name in expected_checks:
            assert check_name in monitor.health_checks, f"Missing health check: {check_name}"

    def test_health_status_aggregation(self):
        """Verify overall status logic based on component failures."""
        monitor = SystemHealthMonitor()
        
        # All healthy
        monitor.metrics.component_statuses = {
            "redis": HealthStatus.HEALTHY,
            "gemini": HealthStatus.HEALTHY
        }
        monitor._update_metrics()
        assert monitor.metrics.overall_status == HealthStatus.HEALTHY
        
        # Non-critical failure -> Degraded
        monitor.metrics.component_statuses["datadog"] = HealthStatus.FAILED
        # We need to mock the critical flag lookup
        monitor.health_checks["datadog"] = MagicMock(critical=False)
        monitor.health_checks["redis"] = MagicMock(critical=True)
        monitor.health_checks["gemini"] = MagicMock(critical=True)
        
        monitor._update_metrics()
        assert monitor.metrics.overall_status == HealthStatus.DEGRADED
        
        # Critical failure -> Critical
        monitor.metrics.component_statuses["redis"] = HealthStatus.FAILED
        monitor._update_metrics()
        assert monitor.metrics.overall_status == HealthStatus.CRITICAL

    @patch('src.system_health.agent_logger')
    def test_alerting_integration(self, mock_logger):
        """Verify alerting callbacks are triggered on critical failures."""
        monitor = SystemHealthMonitor()
        mock_callback = MagicMock()
        monitor.register_alert_callback(mock_callback)
        
        # Simulate critical failure
        monitor.metrics.component_statuses["test_critical"] = HealthStatus.CRITICAL
        monitor._check_alert_conditions()
        
        mock_callback.assert_called_with("test_critical", HealthStatus.CRITICAL)
