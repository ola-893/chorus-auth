
import pytest
import time
from unittest.mock import MagicMock, patch
from hypothesis import given, strategies as st
from datetime import datetime

from src.prediction_engine.alert_delivery_engine import AlertDeliveryEngine, PrioritizedAlert
from src.prediction_engine.models.alert import ClassifiedAlert, AlertSeverity, AlertContext, ImpactAssessment

class TestPropertyAlertDelivery:
    
    def _create_alert(self, severity):
        return ClassifiedAlert(
            severity=severity,
            title=f"Test {severity}",
            description="Test",
            impact=ImpactAssessment(0,0,0,[],""),
            recommended_action="",
            requires_voice_alert=True if severity in [AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY] else False,
            context=AlertContext("test", [], timestamp=datetime.now()),
            timestamp=datetime.now()
        )

    def test_priority_queue_ordering(self):
        """
        Property 4: Real-time alert delivery performance (Prioritization).
        Higher priority alerts (EMERGENCY) should be dequeued before lower priority ones (INFO),
        regardless of insertion order.
        """
        engine = AlertDeliveryEngine()
        
        # Create alerts
        alert_emergency = self._create_alert(AlertSeverity.EMERGENCY)
        alert_info = self._create_alert(AlertSeverity.INFO)
        
        # Insert Low priority first
        engine.process_alert(alert_info)
        # Insert High priority second
        engine.process_alert(alert_emergency)
        
        # Check queue
        first_item = engine.alert_queue.get()
        second_item = engine.alert_queue.get()
        
        # Emergency (Priority 1) should come before Info (Priority 4)
        assert first_item.alert.severity == AlertSeverity.EMERGENCY
        assert second_item.alert.severity == AlertSeverity.INFO

    @patch('src.prediction_engine.alert_delivery_engine.voice_client')
    def test_channel_routing(self, mock_voice):
        """Test proper routing to channels based on alert config."""
        engine = AlertDeliveryEngine()
        mock_voice.enabled = True
        
        # Critical alert -> Voice + System
        alert_crit = self._create_alert(AlertSeverity.CRITICAL)
        engine._deliver_alert(alert_crit)
        
        assert mock_voice.generate_alert.called
        
        # Reset
        mock_voice.reset_mock()
        
        # Info alert -> System only (requires_voice_alert=False)
        alert_info = self._create_alert(AlertSeverity.INFO)
        engine._deliver_alert(alert_info)
        
        assert not mock_voice.generate_alert.called
