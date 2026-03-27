import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.api.main import app
from src.config import settings

client = TestClient(app)

@pytest.fixture
def mock_kafka():
    with patch("src.api.universal_router.kafka_bus") as mock:
        yield mock

@pytest.fixture
def api_key():
    return "test-key"

    def test_ingest_observations_success(mock_kafka, api_key):
        # Enable Kafka for this test
        with patch("src.config.settings.kafka.enabled", True):
            payload = {
                "source_system": "TestSwarm",
                "events": [
                    {
                        "network_id": "net-1",
                        "event_id": "evt-1",
                        "agent_id": "agent-1",
                        "event_type": "message",
                        "payload": {"text": "hello"}
                    }
                ]
            }
            
            response = client.post(
                "/v1/universal/observe",
                json=payload,
                headers={"X-Agent-API-Key": api_key}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "accepted"
            assert data["ingested_count"] == 1
            
            mock_kafka.produce.assert_called_once()
            args = mock_kafka.produce.call_args[1]
            assert args["topic"] == settings.kafka.agent_messages_topic
            assert args["key"] == "agent-1"
            assert args["value"]["metadata"]["source"] == "universal_api"

    def test_ingest_observations_kafka_disabled(api_key):
        with patch("src.config.settings.kafka.enabled", False):
            payload = {
                "source_system": "TestSwarm",
                "events": []
            }
            response = client.post(
                "/v1/universal/observe",
                json=payload,
                headers={"X-Agent-API-Key": api_key}
            )
            assert response.status_code == 503

    def test_ingest_observations_invalid_schema(api_key):
        with patch("src.config.settings.kafka.enabled", True):
            payload = {
                "source_system": "TestSwarm",
                "events": [
                    {
                        # Missing network_id, event_id
                        "agent_id": "agent-1",
                        "event_type": "message"
                    }
                ]
            }
            response = client.post(
                "/v1/universal/observe",
                json=payload,
                headers={"X-Agent-API-Key": api_key}
            )
            assert response.status_code == 422 # Validation Error
def test_register_webhook(api_key):
    response = client.post(
        "/v1/universal/webhooks/register",
        params={"url": "http://example.com/hook", "network_id": "net-1"},
        headers={"X-Agent-API-Key": api_key}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "registered"
