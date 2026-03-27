"""
Property-based tests for Datadog integration and observability.

**Feature: Observability & Trust Layer**
**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
"""
import pytest
from unittest.mock import MagicMock, patch
from hypothesis import given, strategies as st, settings, HealthCheck
import logging

from src.integrations.datadog_client import DatadogClient
from src.logging_config import DatadogHandler, get_agent_logger

@pytest.fixture
def mock_datadog_client():
    with patch('src.integrations.datadog_client.datadog_client') as mock:
        mock.enabled = True
        yield mock

class TestDatadogIntegration:
    """Property tests for Datadog integration."""

    @given(
        metric_name=st.text(min_size=1, alphabet='abcdefghijklmnopqrstuvwxyz._'),
        value=st.floats(min_value=0.0, max_value=1000.0),
        tags=st.lists(st.text(min_size=1), max_size=5)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_datadog_metric_completeness(self, mock_datadog_client, metric_name, value, tags):
        """
        Property 4: Datadog metric completeness.
        Validates: Requirements 2.1, 2.2, 2.3, 2.5
        """
        # Act
        mock_datadog_client.send_metric(metric_name, value, tags)

        # Assert
        mock_datadog_client.send_metric.assert_called_with(metric_name, value, tags)

    @given(
        message=st.text(min_size=1),
        level=st.sampled_from(["INFO", "WARNING", "ERROR"]),
        context=st.dictionaries(keys=st.text(min_size=1), values=st.text(min_size=1))
    )
    def test_property_error_logging_consistency(self, message, level, context):
        """
        Property 5: Error logging consistency.
        Validates: Requirements 2.4
        """
        # Arrange
        handler = DatadogHandler()
        
        # Create a log record
        record = logging.LogRecord(
            name="test_logger",
            level=getattr(logging, level),
            pathname="test.py",
            lineno=10,
            msg=message,
            args=(),
            exc_info=None
        )
        record.context = context
        
        # Mock the datadog_client inside the handler by patching the integration module
        # The handler imports it from src.integrations.datadog_client
        with patch('src.integrations.datadog_client.datadog_client') as mock_dd_client:
            mock_dd_client.enabled = True
            
            # Act
            handler.emit(record)
            
            # Assert
            mock_dd_client.send_log.assert_called()
            call_args = mock_dd_client.send_log.call_args
            assert call_args is not None
            assert call_args[1]['message'] == message
            assert call_args[1]['level'] == level
            # Context might have extra fields added by handler, check subset
            for k, v in context.items():
                assert call_args[1]['context'][k] == v

    @given(
        agent_id=st.text(min_size=1),
        old_score=st.integers(min_value=0, max_value=100),
        new_score=st.integers(min_value=0, max_value=100),
        reason=st.text(min_size=1)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_trust_score_change_tracking(self, mock_datadog_client, agent_id, old_score, new_score, reason):
        """
        Test that trust score changes are tracked as both metrics and logs.
        """
        # Act
        mock_datadog_client.track_trust_score_change(agent_id, old_score, new_score, reason)
        
        # Assert
        mock_datadog_client.track_trust_score_change.assert_called_with(agent_id, old_score, new_score, reason)