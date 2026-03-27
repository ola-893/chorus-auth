"""
Property-based tests for Datadog alerting functionality.

**Feature: observability-trust-layer, Property 8: Alert threshold triggering**
**Validates: Requirements 4.3, 4.4**

**Feature: observability-trust-layer, Property 9: Alert resolution automation**
**Validates: Requirements 4.5**
"""
import pytest
from hypothesis import given, strategies as st, assume, settings as hypothesis_settings
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from typing import List, Dict, Any
import asyncio

from src.integrations.datadog_alerting import DatadogAlertingManager
from src.config import settings


# Test data generators
@st.composite
def trust_score_generator(draw):
    """Generate valid trust scores."""
    return draw(st.floats(min_value=0.0, max_value=100.0))


@st.composite
def agent_id_generator(draw):
    """Generate valid agent IDs."""
    return draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))


@st.composite
def alert_condition_generator(draw):
    """Generate alert conditions for testing."""
    condition_type = draw(st.sampled_from(['trust_score_low', 'multiple_quarantines', 'system_health_degraded', 'conflict_rate_high']))
    
    if condition_type == 'trust_score_low':
        return {
            'type': condition_type,
            'agent_id': draw(agent_id_generator()),
            'trust_score': draw(st.floats(min_value=0.0, max_value=29.9)),  # Below threshold
            'threshold': 30.0
        }
    elif condition_type == 'multiple_quarantines':
        return {
            'type': condition_type,
            'quarantined_count': draw(st.integers(min_value=4, max_value=20)),  # Above threshold
            'threshold': 3,
            'time_window': draw(st.integers(min_value=1, max_value=60))
        }
    elif condition_type == 'system_health_degraded':
        return {
            'type': condition_type,
            'component': draw(st.sampled_from(['redis', 'datadog', 'gemini', 'api'])),
            'status': draw(st.sampled_from(['unhealthy', 'degraded', 'failed']))
        }
    else:  # conflict_rate_high
        return {
            'type': condition_type,
            'conflict_rate': draw(st.floats(min_value=0.8, max_value=2.0)),  # Above normal
            'threshold': 0.7,
            'time_window': draw(st.integers(min_value=1, max_value=60))
        }


@st.composite
def alert_resolution_generator(draw):
    """Generate alert resolution scenarios."""
    return {
        'alert_id': draw(st.text(min_size=1, max_size=20)),
        'resolution_type': draw(st.sampled_from(['automatic', 'manual'])),
        'resolved_at': datetime.now(),
        'resolution_reason': draw(st.sampled_from(['condition_cleared', 'threshold_adjusted', 'manual_override']))
    }


class TestAlertThresholdTriggering:
    """Test alert threshold triggering property."""
    
    @given(alert_condition_generator())
    @hypothesis_settings(max_examples=100)
    def test_alert_threshold_triggering_property(self, alert_condition):
        """
        **Feature: observability-trust-layer, Property 8: Alert threshold triggering**
        **Validates: Requirements 4.3, 4.4**
        
        For any system condition that exceeds configured thresholds, 
        appropriate alerts should be triggered in Datadog with correct severity levels.
        """
        # Mock the Datadog client and monitor API
        with patch('src.integrations.datadog_alerting.MonitorsApi') as mock_monitors_api, \
             patch('src.integrations.datadog_alerting.ApiClient') as mock_api_client:
            
            mock_api_instance = Mock()
            mock_monitors_api.return_value = mock_api_instance
            mock_api_instance.create_monitor = Mock()
            mock_api_instance.search_monitors = Mock()
            
            # Create alerting manager instance
            alerting_manager = DatadogAlertingManager()
            
            # Test alert triggering based on condition type
            if alert_condition['type'] == 'trust_score_low':
                # Test trust score alert
                agent_id = alert_condition['agent_id']
                trust_score = alert_condition['trust_score']
                
                # Trigger the alert condition
                alerting_manager.check_trust_score_alert(agent_id, trust_score)
                
                # Verify alert was triggered with correct severity
                expected_severity = 'critical' if trust_score < 20 else 'warning'
                assert alerting_manager.should_trigger_alert('trust_score_low', trust_score, 30.0)
                assert alerting_manager.get_alert_severity('trust_score_low', trust_score) == expected_severity
                
            elif alert_condition['type'] == 'multiple_quarantines':
                # Test multiple quarantines alert
                quarantined_count = alert_condition['quarantined_count']
                threshold = alert_condition['threshold']
                
                # Trigger the alert condition
                alerting_manager.check_multiple_quarantines_alert(quarantined_count, threshold)
                
                # Verify alert was triggered with critical severity
                assert alerting_manager.should_trigger_alert('multiple_quarantines', quarantined_count, threshold)
                assert alerting_manager.get_alert_severity('multiple_quarantines', quarantined_count) == 'critical'
                
            elif alert_condition['type'] == 'system_health_degraded':
                # Test system health alert
                component = alert_condition['component']
                status = alert_condition['status']
                
                # Trigger the alert condition
                alerting_manager.check_system_health_alert(component, status)
                
                # Verify alert was triggered with appropriate severity
                expected_severity = 'critical' if status == 'failed' else 'warning'
                assert alerting_manager.should_trigger_alert('system_health', status, 'healthy')
                assert alerting_manager.get_alert_severity('system_health', status) == expected_severity
                
            elif alert_condition['type'] == 'conflict_rate_high':
                # Test conflict rate alert
                conflict_rate = alert_condition['conflict_rate']
                threshold = alert_condition['threshold']
                
                # Trigger the alert condition
                alerting_manager.check_conflict_rate_alert(conflict_rate, threshold)
                
                # Verify alert was triggered with appropriate severity
                expected_severity = 'critical' if conflict_rate > 1.0 else 'warning'
                assert alerting_manager.should_trigger_alert('conflict_rate', conflict_rate, threshold)
                assert alerting_manager.get_alert_severity('conflict_rate', conflict_rate) == expected_severity


class TestAlertResolutionAutomation:
    """Test alert resolution automation property."""
    
    @given(alert_condition_generator(), alert_resolution_generator())
    @hypothesis_settings(max_examples=100)
    def test_alert_resolution_automation_property(self, alert_condition, alert_resolution):
        """
        **Feature: observability-trust-layer, Property 9: Alert resolution automation**
        **Validates: Requirements 4.5**
        
        For any alert condition that resolves, the corresponding alert should be 
        automatically closed and recovery notifications sent.
        """
        # Mock the Datadog client and monitor API
        with patch('src.integrations.datadog_alerting.MonitorsApi') as mock_monitors_api, \
             patch('src.integrations.datadog_alerting.ApiClient') as mock_api_client:
            
            mock_api_instance = Mock()
            mock_monitors_api.return_value = mock_api_instance
            mock_api_instance.resolve_monitor = Mock()
            mock_api_instance.get_monitor = Mock()
            
            # Create alerting manager instance
            alerting_manager = DatadogAlertingManager()
            
            # Enable the alerting manager for testing
            alerting_manager.enabled = True
            
            # Mock the send_recovery_notification method to avoid datadog_client import issues
            alerting_manager.send_recovery_notification = AsyncMock()
            
            # First create an alert to resolve
            created_alert_id = alerting_manager.process_alert_condition(alert_condition)
            
            # Only test resolution if an alert was actually created
            if created_alert_id and alerting_manager.is_alert_active(created_alert_id):
                resolution_reason = alert_resolution['resolution_reason']
                
                # Test automatic resolution
                alerting_manager.resolve_alert_automatically(created_alert_id, resolution_reason)
                
                # Verify alert was resolved
                assert alerting_manager.is_alert_resolved(created_alert_id)
                
                # Verify recovery notification was sent
                assert alerting_manager.was_recovery_notification_sent(created_alert_id)
                
                # Test that resolution is idempotent
                # Resolving an already resolved alert should not cause errors
                alerting_manager.resolve_alert_automatically(created_alert_id, resolution_reason)
                assert alerting_manager.is_alert_resolved(created_alert_id)
                
                # Test that resolution includes proper metadata
                resolution_metadata = alerting_manager.get_resolution_metadata(created_alert_id)
                assert resolution_metadata is not None
                assert 'resolved_at' in resolution_metadata
                assert 'resolution_reason' in resolution_metadata
                assert resolution_metadata['resolution_reason'] == resolution_reason
                
                # Verify alert is no longer active
                assert not alerting_manager.is_alert_active(created_alert_id)
                
                # Verify resolution timestamp is recent
                resolved_at = resolution_metadata['resolved_at']
                assert isinstance(resolved_at, datetime)
                assert (datetime.now() - resolved_at).total_seconds() < 5  # Within 5 seconds
    
    @given(alert_condition_generator())
    @hypothesis_settings(max_examples=50)
    def test_automatic_condition_detection_and_resolution(self, alert_condition):
        """
        **Feature: observability-trust-layer, Property 9: Alert resolution automation**
        **Validates: Requirements 4.5**
        
        For any alert condition that clears, the system should automatically detect 
        the condition clearing and resolve the alert with recovery notifications.
        """
        # Mock the Datadog client
        with patch('src.integrations.datadog_alerting.MonitorsApi') as mock_monitors_api, \
             patch('src.integrations.datadog_alerting.ApiClient') as mock_api_client:
            
            mock_api_instance = Mock()
            mock_monitors_api.return_value = mock_api_instance
            
            # Create alerting manager instance
            alerting_manager = DatadogAlertingManager()
            
            # Enable the alerting manager for testing
            alerting_manager.enabled = True
            
            # Mock the send_recovery_notification method to avoid datadog_client import issues
            alerting_manager.send_recovery_notification = AsyncMock()
            
            # Create an alert first
            created_alert_id = alerting_manager.process_alert_condition(alert_condition)
            
            if created_alert_id and alerting_manager.is_alert_active(created_alert_id):
                alert_type = alert_condition['type']
                
                # Create system state that would clear the alert condition
                clearing_system_state = {}
                
                if alert_type == 'trust_score_low':
                    # Trust score above threshold should clear the alert
                    clearing_system_state = {'trust_score': 40.0}  # Above 35 threshold
                elif alert_type == 'multiple_quarantines':
                    # No quarantined agents should clear the alert
                    clearing_system_state = {'quarantined_count': 0}
                elif alert_type == 'system_health_degraded':
                    # Healthy status should clear the alert
                    clearing_system_state = {'component_status': 'healthy'}
                elif alert_type == 'conflict_rate_high':
                    # Low conflict rate should clear the alert
                    clearing_system_state = {'conflict_rate': 0.5}  # Below 0.6 threshold
                
                # Map alert types to the types used in check_auto_resolution_conditions
                resolution_alert_type = alert_type
                if alert_type == 'system_health_degraded':
                    resolution_alert_type = 'system_health'
                elif alert_type == 'conflict_rate_high':
                    resolution_alert_type = 'conflict_rate'
                
                # Test automatic condition detection
                should_resolve = alerting_manager.check_auto_resolution_conditions(resolution_alert_type, clearing_system_state)
                assert should_resolve, f"Auto-resolution conditions should be met for {resolution_alert_type} with state {clearing_system_state}"
                
                # Test the complete auto-resolution process
                # For the test, we need to simulate the stability check by calling multiple times
                # First, set the alert as older than 1 minute to pass the minimum age check
                alert_data = alerting_manager.active_alerts[created_alert_id]
                alert_data["triggered_at"] = datetime.now() - timedelta(minutes=2)
                
                # Mock the stable resolution check to return True for testing
                original_check = alerting_manager._check_stable_resolution_conditions
                async def mock_stable_check(alert_id, alert_type, current_values):
                    return alerting_manager.check_auto_resolution_conditions(alert_type, current_values)
                
                alerting_manager._check_stable_resolution_conditions = mock_stable_check
                
                try:
                    asyncio.run(alerting_manager.process_auto_resolution(clearing_system_state))
                    
                    # Verify alert was automatically resolved
                    assert alerting_manager.is_alert_resolved(created_alert_id), f"Alert {created_alert_id} should be resolved after auto-resolution process"
                finally:
                    # Restore original method
                    alerting_manager._check_stable_resolution_conditions = original_check
                
                # Verify recovery notification was sent
                assert alerting_manager.was_recovery_notification_sent(created_alert_id)
                
                # Verify recovery notification method was called
                alerting_manager.send_recovery_notification.assert_called()
                
                # Verify resolution metadata indicates automatic resolution
                resolution_metadata = alerting_manager.get_resolution_metadata(created_alert_id)
                assert resolution_metadata is not None
                assert resolution_metadata['resolution_reason'] == 'condition_cleared'


class TestAlertingIntegration:
    """Integration tests for alerting functionality."""
    
    @given(
        st.lists(alert_condition_generator(), min_size=1, max_size=10),
        st.lists(alert_resolution_generator(), min_size=1, max_size=5)
    )
    @hypothesis_settings(max_examples=50)
    def test_alerting_workflow_property(self, alert_conditions, alert_resolutions):
        """
        Test complete alerting workflow from trigger to resolution.
        """
        with patch('src.integrations.datadog_alerting.MonitorsApi') as mock_monitors_api, \
             patch('src.integrations.datadog_alerting.ApiClient') as mock_api_client:
            
            mock_api_instance = Mock()
            mock_monitors_api.return_value = mock_api_instance
            
            alerting_manager = DatadogAlertingManager()
            
            # Track triggered alerts
            triggered_alerts = []
            
            # Process all alert conditions
            for condition in alert_conditions:
                alert_id = alerting_manager.process_alert_condition(condition)
                if alert_id:
                    triggered_alerts.append(alert_id)
            
            # Verify alerts were triggered appropriately
            for alert_id in triggered_alerts:
                assert alerting_manager.is_alert_active(alert_id)
            
            # Process resolutions
            for i, resolution in enumerate(alert_resolutions):
                if i < len(triggered_alerts):
                    alert_id = triggered_alerts[i]
                    alerting_manager.resolve_alert_automatically(alert_id, resolution['resolution_reason'])
                    
                    # Verify resolution
                    assert alerting_manager.is_alert_resolved(alert_id)
                    assert not alerting_manager.is_alert_active(alert_id)