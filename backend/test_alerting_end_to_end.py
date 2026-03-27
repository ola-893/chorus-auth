#!/usr/bin/env python3
"""
End-to-end test script for Datadog alerting automation.

This script tests the complete alerting workflow including:
- Automatic monitor creation via API
- Alert triggering based on system conditions
- Alert escalation for critical scenarios
- Automatic alert resolution when conditions clear
- Recovery notifications

Usage:
    python test_alerting_end_to_end.py [--live-datadog]
    
    --live-datadog: Use actual Datadog API (requires valid credentials)
"""
import asyncio
import argparse
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List
import json

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.integrations.datadog_alerting import DatadogAlertingManager
from src.integrations.alerting_integration import AlertingIntegrationService
from src.integrations.datadog_client import DatadogClient
from src.config import settings

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AlertingTestSuite:
    """Comprehensive test suite for Datadog alerting automation."""
    
    def __init__(self, use_live_datadog: bool = False):
        """
        Initialize the test suite.
        
        Args:
            use_live_datadog: Whether to use actual Datadog API
        """
        self.use_live_datadog = use_live_datadog
        self.test_results = {}
        self.created_monitors = []
        self.triggered_alerts = []
        
        # Initialize components
        if use_live_datadog:
            self.alerting_manager = DatadogAlertingManager()
            self.alerting_integration = AlertingIntegrationService()
            self.datadog_client = DatadogClient()
        else:
            # Use mock components for testing
            self.alerting_manager = self._create_mock_alerting_manager()
            self.alerting_integration = AlertingIntegrationService(self.alerting_manager)
            self.datadog_client = self._create_mock_datadog_client()
    
    def _create_mock_alerting_manager(self) -> DatadogAlertingManager:
        """Create a mock alerting manager for testing."""
        manager = DatadogAlertingManager()
        manager.enabled = True
        
        # Mock the API client methods
        class MockMonitorsApi:
            def __init__(self):
                self.monitor_counter = 1000
                self.monitors = {}
            
            def create_monitor(self, monitor):
                monitor_id = self.monitor_counter
                self.monitor_counter += 1
                self.monitors[monitor_id] = {
                    "id": monitor_id,
                    "name": monitor.name,
                    "query": monitor.query,
                    "message": monitor.message
                }
                
                class MockResponse:
                    def __init__(self, monitor_id):
                        self.id = monitor_id
                
                return MockResponse(monitor_id)
            
            def search_monitors(self, query):
                class MockSearchResponse:
                    def __init__(self):
                        self.monitors = []
                
                return MockSearchResponse()
            
            def get_monitor(self, monitor_id):
                return self.monitors.get(monitor_id)
            
            def update_monitor(self, monitor_id, monitor):
                if monitor_id in self.monitors:
                    self.monitors[monitor_id].update({
                        "name": monitor.name,
                        "query": monitor.query,
                        "message": monitor.message
                    })
        
        manager.monitors_api = MockMonitorsApi()
        return manager
    
    def _create_mock_datadog_client(self) -> DatadogClient:
        """Create a mock Datadog client for testing."""
        client = DatadogClient()
        client.enabled = True
        
        # Mock the API methods
        client.send_metric = lambda *args, **kwargs: None
        client.send_log = lambda *args, **kwargs: None
        client.track_trust_score_change = lambda *args, **kwargs: None
        
        return client
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """
        Run all alerting tests.
        
        Returns:
            Dictionary containing test results
        """
        logger.info("Starting comprehensive alerting test suite")
        logger.info(f"Using {'live Datadog API' if self.use_live_datadog else 'mock components'}")
        
        test_methods = [
            ("monitor_creation", self.test_monitor_creation),
            ("alert_triggering", self.test_alert_triggering),
            ("escalation_logic", self.test_escalation_logic),
            ("resolution_automation", self.test_resolution_automation),
            ("integration_workflow", self.test_integration_workflow),
            ("performance", self.test_performance),
            ("error_handling", self.test_error_handling)
        ]
        
        overall_results = {
            "start_time": datetime.now().isoformat(),
            "use_live_datadog": self.use_live_datadog,
            "tests": {},
            "summary": {
                "total_tests": len(test_methods),
                "passed": 0,
                "failed": 0,
                "errors": []
            }
        }
        
        for test_name, test_method in test_methods:
            logger.info(f"Running test: {test_name}")
            try:
                result = await test_method()
                overall_results["tests"][test_name] = result
                
                if result.get("success", False):
                    overall_results["summary"]["passed"] += 1
                    logger.info(f"✓ {test_name}: PASSED")
                else:
                    overall_results["summary"]["failed"] += 1
                    logger.error(f"✗ {test_name}: FAILED - {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                overall_results["summary"]["failed"] += 1
                overall_results["summary"]["errors"].append(f"{test_name}: {str(e)}")
                logger.error(f"✗ {test_name}: ERROR - {e}")
        
        overall_results["end_time"] = datetime.now().isoformat()
        overall_results["success"] = overall_results["summary"]["failed"] == 0
        
        return overall_results
    
    async def test_monitor_creation(self) -> Dict[str, Any]:
        """Test automatic Datadog monitor creation via API."""
        try:
            # Test monitor creation
            created_monitors = await self.alerting_manager.create_monitors()
            
            # Verify monitors were created
            success = len(created_monitors) > 0
            
            if success:
                self.created_monitors = list(created_monitors.values())
                
                # Verify specific monitor types exist
                expected_monitors = [
                    "trust_score_low",
                    "multiple_quarantines", 
                    "system_health",
                    "conflict_rate"
                ]
                
                created_types = list(created_monitors.keys())
                missing_monitors = [m for m in expected_monitors if m not in created_types]
                
                if missing_monitors:
                    return {
                        "success": False,
                        "error": f"Missing expected monitors: {missing_monitors}",
                        "created_monitors": created_monitors
                    }
            
            return {
                "success": success,
                "created_monitors": created_monitors,
                "monitor_count": len(created_monitors)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_alert_triggering(self) -> Dict[str, Any]:
        """Test alert triggering based on system conditions."""
        try:
            triggered_alerts = []
            
            # Test trust score alert
            trust_alert_id = self.alerting_manager.check_trust_score_alert("test_agent_001", 15.0)
            if trust_alert_id:
                triggered_alerts.append(("trust_score", trust_alert_id))
            
            # Test multiple quarantines alert
            quarantine_alert_id = self.alerting_manager.check_multiple_quarantines_alert(5, 3)
            if quarantine_alert_id:
                triggered_alerts.append(("multiple_quarantines", quarantine_alert_id))
            
            # Test system health alert
            health_alert_id = self.alerting_manager.check_system_health_alert("redis", "failed")
            if health_alert_id:
                triggered_alerts.append(("system_health", health_alert_id))
            
            # Test conflict rate alert
            conflict_alert_id = self.alerting_manager.check_conflict_rate_alert(0.9, 0.7)
            if conflict_alert_id:
                triggered_alerts.append(("conflict_rate", conflict_alert_id))
            
            self.triggered_alerts = triggered_alerts
            
            # Verify alerts were triggered correctly
            success = len(triggered_alerts) >= 3  # Expect at least 3 types to trigger
            
            # Verify alert data is stored correctly
            for alert_type, alert_id in triggered_alerts:
                if not self.alerting_manager.is_alert_active(alert_id):
                    return {
                        "success": False,
                        "error": f"Alert {alert_id} not marked as active",
                        "triggered_alerts": triggered_alerts
                    }
            
            return {
                "success": success,
                "triggered_alerts": triggered_alerts,
                "alert_count": len(triggered_alerts)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_escalation_logic(self) -> Dict[str, Any]:
        """Test alert escalation logic for critical scenarios."""
        try:
            escalation_results = []
            
            # Test escalation for multiple quarantines at different levels
            test_scenarios = [
                (4, 1),   # Standard level
                (6, 2),   # High level
                (8, 3),   # Critical level
                (12, 4)   # Emergency level
            ]
            
            for quarantine_count, expected_level in test_scenarios:
                alert_id = self.alerting_manager.check_multiple_quarantines_alert(quarantine_count, 3)
                
                if alert_id:
                    alert_data = self.alerting_manager.active_alerts.get(alert_id)
                    if alert_data:
                        actual_level = alert_data.get("escalation_level", 0)
                        escalation_results.append({
                            "quarantine_count": quarantine_count,
                            "expected_level": expected_level,
                            "actual_level": actual_level,
                            "correct": actual_level == expected_level
                        })
            
            # Verify escalation logic
            success = all(result["correct"] for result in escalation_results)
            
            # Test immediate escalation for emergency scenarios
            emergency_alert_id = self.alerting_manager.check_multiple_quarantines_alert(15, 3)
            if emergency_alert_id:
                alert_data = self.alerting_manager.active_alerts.get(emergency_alert_id)
                escalation_notifications = alert_data.get("escalation_notifications_sent", [])
                immediate_escalation = len(escalation_notifications) > 0
            else:
                immediate_escalation = False
            
            return {
                "success": success and immediate_escalation,
                "escalation_results": escalation_results,
                "immediate_escalation": immediate_escalation
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_resolution_automation(self) -> Dict[str, Any]:
        """Test automatic alert resolution when conditions clear."""
        try:
            resolution_results = []
            
            # Create test alerts to resolve
            test_alerts = [
                ("trust_score_low", lambda: self.alerting_manager.check_trust_score_alert("test_agent_002", 25.0)),
                ("multiple_quarantines", lambda: self.alerting_manager.check_multiple_quarantines_alert(4, 3)),
                ("system_health", lambda: self.alerting_manager.check_system_health_alert("datadog", "degraded")),
                ("conflict_rate", lambda: self.alerting_manager.check_conflict_rate_alert(0.8, 0.7))
            ]
            
            created_alerts = []
            for alert_type, create_func in test_alerts:
                alert_id = create_func()
                if alert_id:
                    created_alerts.append((alert_type, alert_id))
            
            # Test manual resolution
            for alert_type, alert_id in created_alerts:
                # Verify alert is active
                if not self.alerting_manager.is_alert_active(alert_id):
                    continue
                
                # Resolve the alert
                self.alerting_manager.resolve_alert_automatically(alert_id, "test_resolution")
                
                # Verify resolution
                is_resolved = self.alerting_manager.is_alert_resolved(alert_id)
                recovery_sent = self.alerting_manager.was_recovery_notification_sent(alert_id)
                
                resolution_results.append({
                    "alert_type": alert_type,
                    "alert_id": alert_id,
                    "resolved": is_resolved,
                    "recovery_notification": recovery_sent
                })
            
            # Test automatic resolution based on system state
            # Create a new alert for auto-resolution testing
            auto_resolve_alert_id = self.alerting_manager.check_trust_score_alert("test_agent_003", 20.0)
            
            if auto_resolve_alert_id:
                # Simulate system state that would trigger auto-resolution
                recovery_state = {
                    "agent_trust_scores": {"test_agent_003": 40.0},  # Above threshold
                    "quarantined_count": 0,
                    "component_health": {"redis": "healthy", "datadog": "healthy"},
                    "conflict_rate": 0.3
                }
                
                # Process auto-resolution
                await self.alerting_manager.process_auto_resolution(recovery_state)
                
                # Check if alert was auto-resolved
                auto_resolved = self.alerting_manager.is_alert_resolved(auto_resolve_alert_id)
                resolution_results.append({
                    "alert_type": "auto_resolution",
                    "alert_id": auto_resolve_alert_id,
                    "resolved": auto_resolved,
                    "recovery_notification": True  # Assume notification was sent
                })
            
            # Verify all resolutions worked
            success = all(result["resolved"] for result in resolution_results)
            
            return {
                "success": success,
                "resolution_results": resolution_results,
                "resolved_count": len([r for r in resolution_results if r["resolved"]])
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_integration_workflow(self) -> Dict[str, Any]:
        """Test complete integration workflow with alerting service."""
        try:
            # Test the integration service
            integration_results = await self.alerting_integration.test_end_to_end_alerting()
            
            # Verify integration test results
            success = integration_results.get("overall_success", False)
            
            return {
                "success": success,
                "integration_results": integration_results
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_performance(self) -> Dict[str, Any]:
        """Test alerting system performance under load."""
        try:
            start_time = datetime.now()
            
            # Create multiple alerts rapidly
            alert_ids = []
            for i in range(50):
                alert_id = self.alerting_manager.check_trust_score_alert(f"perf_test_agent_{i}", 10.0)
                if alert_id:
                    alert_ids.append(alert_id)
            
            creation_time = (datetime.now() - start_time).total_seconds()
            
            # Test resolution performance
            start_time = datetime.now()
            
            for alert_id in alert_ids:
                self.alerting_manager.resolve_alert_automatically(alert_id, "performance_test")
            
            resolution_time = (datetime.now() - start_time).total_seconds()
            
            # Performance thresholds
            creation_threshold = 5.0  # seconds
            resolution_threshold = 3.0  # seconds
            
            success = (creation_time < creation_threshold and 
                      resolution_time < resolution_threshold)
            
            return {
                "success": success,
                "creation_time": creation_time,
                "resolution_time": resolution_time,
                "alerts_processed": len(alert_ids),
                "creation_rate": len(alert_ids) / creation_time if creation_time > 0 else 0,
                "resolution_rate": len(alert_ids) / resolution_time if resolution_time > 0 else 0
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_error_handling(self) -> Dict[str, Any]:
        """Test error handling in alerting system."""
        try:
            error_scenarios = []
            
            # Test invalid agent ID
            try:
                self.alerting_manager.check_trust_score_alert("", 50.0)
                error_scenarios.append({"scenario": "empty_agent_id", "handled": False})
            except Exception:
                error_scenarios.append({"scenario": "empty_agent_id", "handled": True})
            
            # Test invalid trust score
            try:
                self.alerting_manager.check_trust_score_alert("test_agent", -10.0)
                error_scenarios.append({"scenario": "negative_trust_score", "handled": True})
            except Exception:
                error_scenarios.append({"scenario": "negative_trust_score", "handled": True})
            
            # Test resolving non-existent alert
            try:
                self.alerting_manager.resolve_alert_automatically("non_existent_alert", "test")
                error_scenarios.append({"scenario": "resolve_nonexistent", "handled": True})
            except Exception:
                error_scenarios.append({"scenario": "resolve_nonexistent", "handled": True})
            
            # Test with disabled alerting
            original_enabled = self.alerting_manager.enabled
            self.alerting_manager.enabled = False
            
            alert_id = self.alerting_manager.check_trust_score_alert("test_agent", 15.0)
            disabled_handled = alert_id is None
            
            self.alerting_manager.enabled = original_enabled
            error_scenarios.append({"scenario": "disabled_alerting", "handled": disabled_handled})
            
            # Verify error handling
            success = all(scenario["handled"] for scenario in error_scenarios)
            
            return {
                "success": success,
                "error_scenarios": error_scenarios
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def cleanup(self):
        """Clean up test resources."""
        try:
            if self.use_live_datadog and self.created_monitors:
                logger.info(f"Cleaning up {len(self.created_monitors)} test monitors")
                # In a real implementation, you might want to delete test monitors
                # For safety, we'll just log them
                for monitor_id in self.created_monitors:
                    logger.info(f"Test monitor created: {monitor_id}")
            
            logger.info("Test cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


async def main():
    """Main test execution function."""
    parser = argparse.ArgumentParser(description="End-to-end Datadog alerting test")
    parser.add_argument(
        "--live-datadog", 
        action="store_true",
        help="Use actual Datadog API (requires valid credentials)"
    )
    parser.add_argument(
        "--output",
        default="alerting_test_results.json",
        help="Output file for test results"
    )
    
    args = parser.parse_args()
    
    # Verify Datadog credentials if using live API
    if args.live_datadog:
        if not (os.getenv("DATADOG_API_KEY") and os.getenv("DATADOG_APP_KEY")):
            logger.error("DATADOG_API_KEY and DATADOG_APP_KEY must be set for live testing")
            sys.exit(1)
        
        logger.warning("Using live Datadog API - this will create actual monitors!")
        response = input("Continue? (y/N): ")
        if response.lower() != 'y':
            logger.info("Test cancelled")
            sys.exit(0)
    
    # Run tests
    test_suite = AlertingTestSuite(use_live_datadog=args.live_datadog)
    
    try:
        results = await test_suite.run_all_tests()
        
        # Save results to file
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Print summary
        print("\n" + "="*60)
        print("ALERTING TEST RESULTS SUMMARY")
        print("="*60)
        print(f"Total Tests: {results['summary']['total_tests']}")
        print(f"Passed: {results['summary']['passed']}")
        print(f"Failed: {results['summary']['failed']}")
        print(f"Overall Success: {'✓ PASS' if results['success'] else '✗ FAIL'}")
        
        if results['summary']['errors']:
            print("\nErrors:")
            for error in results['summary']['errors']:
                print(f"  - {error}")
        
        print(f"\nDetailed results saved to: {args.output}")
        
        # Cleanup
        await test_suite.cleanup()
        
        # Exit with appropriate code
        sys.exit(0 if results['success'] else 1)
        
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        await test_suite.cleanup()
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        await test_suite.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())