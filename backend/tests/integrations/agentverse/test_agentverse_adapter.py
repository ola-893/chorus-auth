import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from src.integrations.base import NetworkConfig
from src.integrations.agentverse.adapter_impl import AgentVerseNetworkAdapter

# Mock Data
SAMPLE_MSG = {
    "uuid": "unique-msg-1",
    "received_at": "2023-01-01T12:00:00Z",
    "envelope": {
        "sender": "agent1...",
        "target": "agentMe",
        "payload": "eyJ0ZXh0IjogImhpIn0=" # {"text": "hi"} base64
    }
}

@pytest.fixture
def mock_redis():
    r = MagicMock()
    r.exists.return_value = False 
    return r

@pytest.fixture
def mock_config():
    return NetworkConfig(
        network_id="agentverse-test",
        api_key="test-key",
        endpoint_url="agent1-monitored"
    )

@pytest.fixture
def adapter(mock_config):
    # Mock internal components
    with patch("src.integrations.agentverse.adapter_impl.AgentVerseClient") as MockClient:
        client_instance = MockClient.return_value
        client_instance.get_mailbox_messages = AsyncMock(return_value=[SAMPLE_MSG])
        
        adapter = AgentVerseNetworkAdapter(config=mock_config)
        adapter.client = client_instance
        return adapter

@pytest.mark.asyncio
async def test_poll_new_message(adapter):
    # Inject Redis mock manually since it's lazy loaded or imported
    adapter.redis = MagicMock()
    adapter.redis.exists.return_value = False
    
    # Mock push_observation to avoid Kafka dependency in unit test
    adapter.push_observation = AsyncMock()
    
    await adapter.poll()
    
    # Verify Redis check
    adapter.redis.exists.assert_called_with("chorus:av:msg:unique-msg-1")
    
    # Verify Observation Push
    adapter.push_observation.assert_called_once()
    observation = adapter.push_observation.call_args[0][0]
    assert observation.network_id == "agentverse"
    assert observation.event_id == "unique-msg-1"
    assert observation.agent_id == "agent1..." # From sender
    
    # Verify Redis set
    adapter.redis.set.assert_called_once()

@pytest.mark.asyncio
async def test_poll_duplicate_message(adapter):
    adapter.redis = MagicMock()
    adapter.redis.exists.return_value = True # Exists
    
    adapter.push_observation = AsyncMock()
    
    await adapter.poll()
    
    # Verify NO Push
    adapter.push_observation.assert_not_called()

@pytest.mark.asyncio
async def test_poll_no_messages(adapter):
    adapter.client.get_mailbox_messages.return_value = []
    adapter.push_observation = AsyncMock()
    
    await adapter.poll()
    adapter.push_observation.assert_not_called()
