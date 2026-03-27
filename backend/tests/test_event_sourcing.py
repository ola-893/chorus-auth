
import pytest
from datetime import datetime, timedelta
import json
from unittest.mock import MagicMock, patch

from src.event_sourcing import EventLogManager
from src.config import settings

class TestEventSourcing:
    @pytest.fixture
    def event_manager(self):
        with patch('src.event_sourcing.kafka_bus') as mock_kafka:
            mock_kafka.enabled = True
            manager = EventLogManager()
            manager.kafka_bus = mock_kafka
            yield manager

    def test_event_replay_from_time_point(self, event_manager):
        """Test event replay from a specific time point (Property 14)."""
        # Setup mock consumer
        mock_consumer = MagicMock()
        event_manager.kafka_bus.create_temporary_consumer.return_value = mock_consumer
        
        # Mock messages
        start_time = datetime.now() - timedelta(hours=1)
        
        # Mock offsets
        event_manager.kafka_bus.get_topic_offsets_for_time.return_value = {0: 100}
        
        # Mock poll results
        msg1 = MagicMock()
        msg1.error.return_value = None
        msg1.value.return_value = json.dumps({"agent_id": "a1", "data": "test1"}).encode('utf-8')
        msg1.timestamp.return_value = (1, int(start_time.timestamp() * 1000))
        msg1.offset.return_value = 100
        msg1.key.return_value = b"a1"
        
        msg2 = MagicMock() # Stop condition
        msg2.timestamp.return_value = (1, int((start_time + timedelta(minutes=1)).timestamp() * 1000))
        
        mock_consumer.poll.side_effect = [msg1, None] # Return msg1 then stop
        
        events = list(event_manager.replay_events("test-topic", start_time=start_time))
        
        assert len(events) == 1
        assert events[0]["value"]["agent_id"] == "a1"
        assert events[0]["offset"] == 100
        
        # Verify seek was called
        mock_consumer.assign.assert_called()

    def test_historical_event_querying(self, event_manager):
        """Test querying historical events by agent (Property 15)."""
        # Setup mock consumer
        mock_consumer = MagicMock()
        event_manager.kafka_bus.create_temporary_consumer.return_value = mock_consumer
        
        # Mock messages with different agents
        def create_msg(agent_id, ts_offset_min):
            msg = MagicMock()
            msg.error.return_value = None
            msg.value.return_value = json.dumps({"agent_id": agent_id}).encode('utf-8')
            msg.timestamp.return_value = (1, int((datetime.now() - timedelta(minutes=ts_offset_min)).timestamp() * 1000))
            msg.key.return_value = agent_id.encode('utf-8')
            return msg

        mock_consumer.poll.side_effect = [
            create_msg("agent1", 10),
            create_msg("agent2", 9),
            create_msg("agent1", 8),
            None
        ]
        
        history = event_manager.get_agent_history("agent1", event_type="message")
        
        assert len(history) == 2
        assert all(e["value"]["agent_id"] == "agent1" for e in history)

