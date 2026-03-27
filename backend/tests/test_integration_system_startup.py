
import pytest
import time
from unittest.mock import patch, MagicMock

# Mock the Kafka client before it's imported by other modules
mock_kafka_bus = MagicMock()

with patch.dict('sys.modules', {'src.integrations.kafka_client': MagicMock(kafka_bus=mock_kafka_bus)}):
    from src.system_lifecycle import SystemLifecycleManager
    from src.config import settings
@pytest.mark.integration
class TestSystemStartup:
    """Integration tests for system startup and initialization."""

    def test_kafka_topic_creation_on_startup(self):
        """Test that Kafka topics are created on system startup."""
        settings.kafka.enabled = True
        
        # Create and run the system lifecycle manager
        lifecycle_manager = SystemLifecycleManager(settings)
        lifecycle_manager.startup()

        # Verify that create_topics was called with the correct topics
        mock_kafka_bus.create_topics.assert_called_once()
        
        # Get the actual call arguments
        call_args, call_kwargs = mock_kafka_bus.create_topics.call_args
        
        # Extract the list of topics from the call arguments
        actual_topics = call_args[0]
        
        # Define the expected topics from the settings
        expected_topics = [
            settings.kafka.topics.agent_messages_raw,
            settings.kafka.topics.agent_decisions_processed,
            settings.kafka.topics.system_alerts
        ]
        
        # Assert that the topics are the same, ignoring order
        assert set(actual_topics) == set(expected_topics)

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
