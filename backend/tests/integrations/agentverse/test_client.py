import pytest
import httpx
from unittest.mock import MagicMock, AsyncMock, patch
from src.integrations.agentverse.client import AgentVerseClient

@pytest.fixture
def client():
    return AgentVerseClient(api_key="test_key")

@pytest.mark.asyncio
async def test_get_mailbox_messages_success(client):
    mock_response = [
        {"uuid": "msg1", "envelope": {"sender": "agent1"}},
        {"uuid": "msg2", "envelope": {"sender": "agent2"}}
    ]
    
    # Mock the response object
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_response
    mock_resp.raise_for_status.return_value = None

    # Mock the client instance
    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_resp

    # Mock the constructor to return the instance via context manager
    with patch("httpx.AsyncClient", return_value=mock_client_instance) as mock_constructor:
        # Configure context manager enter/exit
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        
        messages = await client.get_mailbox_messages("agent_me", limit=5)
        
        assert len(messages) == 2
        assert messages[0]["uuid"] == "msg1"
        
        # Verify call
        mock_client_instance.get.assert_called_once()
        args, kwargs = mock_client_instance.get.call_args
        assert "/v2/agents/agent_me/mailbox" in args[0]
        assert kwargs["params"]["limit"] == 5

@pytest.mark.asyncio
async def test_get_mailbox_messages_error(client):
    # Mock the response object to raise error
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Unauthorized", request=None, response=mock_resp
    )

    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_resp
    mock_client_instance.__aenter__.return_value = mock_client_instance
    mock_client_instance.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_client_instance):
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_mailbox_messages("agent_me")

@pytest.mark.asyncio
async def test_resolve_address_success(client):
    mock_details = {"address": "agent1", "name": "Test Agent"}
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_details
    mock_resp.raise_for_status.return_value = None

    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_resp
    mock_client_instance.__aenter__.return_value = mock_client_instance
    mock_client_instance.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_client_instance):
        result = await client.resolve_address("agent1")
        assert result["name"] == "Test Agent"
        assert "/v1/almanac/resolve/agent1" in mock_client_instance.get.call_args[0][0]
