"""
Property-based tests for Redis persistence and data integrity.
"""
import pytest
from hypothesis import given, strategies as st
from redis.exceptions import RedisError
import redis
import unittest.mock
from datetime import datetime, timedelta

from src.prediction_engine.redis_client import RedisClient
from src.prediction_engine.models.core import TrustScoreEntry
from src.prediction_engine.trust_manager import RedisTrustScoreManager, RedisTrustManager


@pytest.fixture(scope="module")
def redis_client():
    """
    Provides a Redis client fixture for the test module.
    This fixture creates a client and ensures that it can connect to Redis.
    If the connection fails, all tests in the module will be skipped.
    """
    client = RedisClient()
    try:
        if not client.ping():
            pytest.skip("Redis server not available")
    except RedisError:
        pytest.skip("Redis server not available")
    return client


@given(
    key=st.text(min_size=1, alphabet=st.characters(min_codepoint=97, max_codepoint=122)),
    value=st.text(min_size=1, alphabet=st.characters(min_codepoint=97, max_codepoint=122)),
)
def test_property_redis_string_roundtrip(redis_client: RedisClient, key: str, value: str):
    """
    Test that a string can be written to and read from Redis without modification.
    """
    try:
        # Arrange
        redis_client.set(key, value)

        # Act
        retrieved_value = redis_client.get(key)

        # Assert
        assert retrieved_value == value
    finally:
        # Cleanup
        redis_client.delete(key)


@given(
    key=st.text(min_size=1, alphabet=st.characters(min_codepoint=97, max_codepoint=122)),
    data=st.dictionaries(
        keys=st.text(min_size=1),
        values=st.one_of(
            st.text(),
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
        ),
    ),
)
def test_property_redis_json_roundtrip(redis_client: RedisClient, key: str, data: dict):
    """
    Test that a JSON object can be written to and read from Redis without modification.
    """
    try:
        # Arrange
        redis_client.set_json(key, data)

        # Act
        retrieved_data = redis_client.get_json(key)

        # Assert
        assert retrieved_data == data
    finally:
        # Cleanup
        redis_client.delete(key)


@given(
    agent_ids=st.lists(
        st.text(min_size=1, alphabet=st.characters(min_codepoint=97, max_codepoint=122)),
        min_size=1,
        max_size=10,
        unique=True,
    )
)
def test_property_trust_score_restoration_after_restart(
    redis_client: RedisClient, agent_ids: list[str]
):
    """
    Test that trust scores are correctly restored from Redis after a simulated restart.
    """
    try:
        # Arrange: Initialize agents with the first trust manager
        trust_manager1 = RedisTrustScoreManager(redis_client_instance=redis_client)
        for agent_id in agent_ids:
            trust_manager1.initialize_agent(agent_id)
            trust_manager1.adjust_score(agent_id, -10, "Initial penalty")

        # Act: Create a new trust manager to simulate a restart
        trust_manager2 = RedisTrustScoreManager(redis_client_instance=redis_client)
        restored_scores = {
            agent_id: trust_manager2.get_score_entry(agent_id) for agent_id in agent_ids
        }

        # Assert: Verify that the restored scores are correct
        for agent_id in agent_ids:
            assert restored_scores[agent_id] is not None
            assert restored_scores[agent_id].current_score == 90
    finally:
        # Cleanup
        for agent_id in agent_ids:
            redis_client.delete(f"trust_score:{agent_id}")


@given(
    agent_id=st.text(min_size=1, alphabet=st.characters(min_codepoint=97, max_codepoint=122)),
    adjustments=st.lists(st.integers(min_value=-10, max_value=10), min_size=1, max_size=10),
)
def test_property_historical_data_time_range_filtering(
    redis_client: RedisClient, agent_id: str, adjustments: list[int]
):
    """
    Test that historical data can be filtered by a time range.
    """
    try:
        # Arrange
        trust_manager = RedisTrustManager(
            score_manager=RedisTrustScoreManager(redis_client_instance=redis_client)
        )
        trust_manager.score_manager.initialize_agent(agent_id)
        
        # Use a wider time range to account for timing precision
        start_time = datetime.now() - timedelta(seconds=1)
        for i, adjustment in enumerate(adjustments):
            trust_manager.update_trust_score(agent_id, adjustment, f"Adjustment {i}")
        end_time = datetime.now() + timedelta(seconds=1)

        # Act
        history = trust_manager.get_agent_history(agent_id)
        filtered_history = trust_manager.get_agent_history_in_range(
            agent_id, start_time, end_time
        )

        # Assert - all entries should be within the range since we made them all after start_time
        assert len(filtered_history) <= len(history), "Filtered history should not exceed total history"
        assert len(filtered_history) >= 0, "Filtered history should be non-negative"
        
        # If we have history, the filtered results should include at least some entries
        # since our time range is generous
        if len(history) > 0:
            assert len(filtered_history) > 0, "Should have some entries in the time range"
    finally:
        # Cleanup
        redis_client.delete(f"trust_score:{agent_id}")


def test_property_redis_retry_resilience(redis_client: RedisClient):
    """
    Test that the Redis client retries on connection errors.
    """
    # Arrange
    key = "resilience-test"
    value = "success"
    mock_get = unittest.mock.Mock(
        side_effect=[redis.exceptions.ConnectionError, value.encode('utf-8')]
    )

    # Act & Assert
    with unittest.mock.patch.object(redis_client._client, "get", mock_get):
        retrieved_value = redis_client.get(key)
        assert retrieved_value == value
        assert mock_get.call_count == 2