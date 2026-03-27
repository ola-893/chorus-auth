"""
Pytest configuration and fixtures for the agent conflict predictor.
"""
import pytest
from unittest.mock import Mock
from datetime import datetime
from typing import List

from src.prediction_engine.models.core import (
    AgentIntention, AgentMessage, ConflictAnalysis, TrustScoreEntry
)


@pytest.fixture
def sample_agent_intention():
    """Sample agent intention for testing."""
    return AgentIntention(
        agent_id="agent_001",
        resource_type="cpu",
        requested_amount=50,
        priority_level=1,
        timestamp=datetime.now()
    )


@pytest.fixture
def sample_agent_intentions():
    """Sample list of agent intentions for testing."""
    return [
        AgentIntention(
            agent_id="agent_001",
            resource_type="cpu",
            requested_amount=50,
            priority_level=1,
            timestamp=datetime.now()
        ),
        AgentIntention(
            agent_id="agent_002",
            resource_type="cpu",
            requested_amount=75,
            priority_level=2,
            timestamp=datetime.now()
        )
    ]


@pytest.fixture
def sample_conflict_analysis():
    """Sample conflict analysis for testing."""
    return ConflictAnalysis(
        risk_score=0.8,
        confidence_level=0.9,
        affected_agents=["agent_001", "agent_002"],
        predicted_failure_mode="resource_contention",
        nash_equilibrium=None,
        timestamp=datetime.now()
    )


@pytest.fixture
def sample_trust_score_entry():
    """Sample trust score entry for testing."""
    return TrustScoreEntry(
        agent_id="agent_001",
        current_score=85,
        last_updated=datetime.now(),
        adjustment_history=[],
        quarantine_count=0,
        creation_time=datetime.now()
    )


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    mock = Mock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = True
    mock.exists.return_value = False
    return mock


@pytest.fixture
def mock_gemini_client():
    """Mock Gemini client for testing."""
    mock = Mock()
    mock.analyze_conflict_risk.return_value = ConflictAnalysis(
        risk_score=0.5,
        confidence_level=0.8,
        affected_agents=["agent_001"],
        predicted_failure_mode="low_risk",
        nash_equilibrium=None,
        timestamp=datetime.now()
    )
    return mock