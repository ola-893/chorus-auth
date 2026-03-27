"""
Unit tests for Redis trust management system.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.prediction_engine.trust_manager import (
    TrustPolicy, RedisTrustScoreManager, RedisTrustManager
)
from src.prediction_engine.models.core import TrustScoreEntry


class TestTrustPolicy:
    """Test trust policy configuration and adjustment logic."""
    
    def test_apply_adjustment_normal_case(self):
        """Test normal trust score adjustment."""
        result = TrustPolicy.apply_adjustment(50, 10)
        assert result == 60
    
    def test_apply_adjustment_negative(self):
        """Test negative trust score adjustment."""
        result = TrustPolicy.apply_adjustment(50, -20)
        assert result == 30
    
    def test_apply_adjustment_upper_bound(self):
        """Test trust score adjustment at upper bound."""
        result = TrustPolicy.apply_adjustment(95, 10)
        assert result == 100  # Clamped to max
    
    def test_apply_adjustment_lower_bound(self):
        """Test trust score adjustment at lower bound."""
        result = TrustPolicy.apply_adjustment(5, -10)
        assert result == 0  # Clamped to min
    
    def test_policy_constants(self):
        """Test policy constants are properly defined."""
        assert TrustPolicy.MIN_SCORE == 0
        assert TrustPolicy.MAX_SCORE == 100
        assert TrustPolicy.INITIAL_SCORE == 100
        assert TrustPolicy.QUARANTINE_THRESHOLD == 30


class TestRedisTrustScoreManager:
    """Test Redis trust score manager implementation."""
    
    @pytest.fixture
    def mock_redis_client(self):
        """Create mock Redis client."""
        mock_client = Mock()
        mock_client.exists.return_value = False
        mock_client.get_json.return_value = None
        mock_client.set_json.return_value = True
        return mock_client
    
    @pytest.fixture
    def trust_score_manager(self, mock_redis_client):
        """Create trust score manager with mock Redis client."""
        return RedisTrustScoreManager(redis_client_instance=mock_redis_client)
    
    def test_initialization(self, trust_score_manager):
        """Test trust score manager initialization."""
        assert trust_score_manager.key_prefix == "trust_score"
        assert isinstance(trust_score_manager.policy, TrustPolicy)
    
    def test_get_redis_key(self, trust_score_manager):
        """Test Redis key generation."""
        key = trust_score_manager._get_redis_key("agent_123")
        assert key == "trust_score:agent_123"
    
    def test_initialize_agent_success(self, trust_score_manager, mock_redis_client):
        """Test successful agent initialization."""
        agent_id = "test_agent"
        
        entry = trust_score_manager.initialize_agent(agent_id)
        
        assert entry.agent_id == agent_id
        assert entry.current_score == 100
        assert entry.quarantine_count == 0
        assert len(entry.adjustment_history) == 0
        
        # Verify Redis operations
        mock_redis_client.exists.assert_called_once_with("trust_score:test_agent")
        mock_redis_client.set_json.assert_called_once()
    
    def test_initialize_agent_already_exists(self, trust_score_manager, mock_redis_client):
        """Test agent initialization when agent already exists."""
        mock_redis_client.exists.return_value = True
        
        with pytest.raises(ValueError, match="Agent test_agent already has a trust score"):
            trust_score_manager.initialize_agent("test_agent")
    
    def test_adjust_score_success(self, trust_score_manager, mock_redis_client):
        """Test successful score adjustment."""
        agent_id = "test_agent"
        
        # Mock existing entry
        existing_entry = {
            "agent_id": agent_id,
            "current_score": 80,
            "last_updated": datetime.now().isoformat(),
            "adjustment_history": [],
            "quarantine_count": 0,
            "creation_time": datetime.now().isoformat()
        }
        mock_redis_client.get_json.return_value = existing_entry
        
        entry = trust_score_manager.adjust_score(agent_id, -10, "test penalty")
        
        assert entry.current_score == 70
        assert len(entry.adjustment_history) == 1
        assert entry.adjustment_history[0]["adjustment"] == -10
        assert entry.adjustment_history[0]["reason"] == "test penalty"
        
        # Verify Redis operations
        mock_redis_client.get_json.assert_called_once_with("trust_score:test_agent")
        mock_redis_client.set_json.assert_called_once()
    
    def test_adjust_score_agent_not_found(self, trust_score_manager, mock_redis_client):
        """Test score adjustment when agent doesn't exist."""
        mock_redis_client.get_json.return_value = None
        
        with pytest.raises(ValueError, match="Agent test_agent not found"):
            trust_score_manager.adjust_score("test_agent", -10, "test penalty")
    
    def test_adjust_score_quarantine_tracking(self, trust_score_manager, mock_redis_client):
        """Test quarantine count tracking in score adjustment."""
        agent_id = "test_agent"
        
        # Mock existing entry
        existing_entry = {
            "agent_id": agent_id,
            "current_score": 50,
            "last_updated": datetime.now().isoformat(),
            "adjustment_history": [],
            "quarantine_count": 0,
            "creation_time": datetime.now().isoformat()
        }
        mock_redis_client.get_json.return_value = existing_entry
        
        entry = trust_score_manager.adjust_score(agent_id, -20, "quarantine penalty")
        
        assert entry.quarantine_count == 1
    
    def test_get_score_entry_exists(self, trust_score_manager, mock_redis_client):
        """Test getting existing score entry."""
        agent_id = "test_agent"
        
        # Mock existing entry
        existing_entry = {
            "agent_id": agent_id,
            "current_score": 75,
            "last_updated": datetime.now().isoformat(),
            "adjustment_history": [],
            "quarantine_count": 0,
            "creation_time": datetime.now().isoformat()
        }
        mock_redis_client.get_json.return_value = existing_entry
        
        entry = trust_score_manager.get_score_entry(agent_id)
        
        assert entry is not None
        assert entry.agent_id == agent_id
        assert entry.current_score == 75
    
    def test_get_score_entry_not_exists(self, trust_score_manager, mock_redis_client):
        """Test getting non-existent score entry."""
        mock_redis_client.get_json.return_value = None
        
        entry = trust_score_manager.get_score_entry("nonexistent_agent")
        
        assert entry is None


class TestRedisTrustManager:
    """Test Redis trust manager high-level operations."""
    
    @pytest.fixture
    def mock_score_manager(self):
        """Create mock trust score manager."""
        return Mock()
    
    @pytest.fixture
    def trust_manager(self, mock_score_manager):
        """Create trust manager with mock score manager."""
        return RedisTrustManager(score_manager=mock_score_manager)
    
    def test_initialization(self, trust_manager):
        """Test trust manager initialization."""
        assert trust_manager.quarantine_threshold == 30  # From settings
    
    def test_get_trust_score_existing_agent(self, trust_manager, mock_score_manager):
        """Test getting trust score for existing agent."""
        mock_entry = TrustScoreEntry(
            agent_id="test_agent",
            current_score=85,
            last_updated=datetime.now(),
            adjustment_history=[],
            quarantine_count=0,
            creation_time=datetime.now()
        )
        mock_score_manager.get_score_entry.return_value = mock_entry
        
        score = trust_manager.get_trust_score("test_agent")
        
        assert score == 85
        mock_score_manager.get_score_entry.assert_called_once_with("test_agent")
    
    def test_get_trust_score_new_agent(self, trust_manager, mock_score_manager):
        """Test getting trust score for new agent (auto-initialization)."""
        mock_score_manager.get_score_entry.return_value = None
        mock_entry = TrustScoreEntry(
            agent_id="new_agent",
            current_score=100,
            last_updated=datetime.now(),
            adjustment_history=[],
            quarantine_count=0,
            creation_time=datetime.now()
        )
        mock_score_manager.initialize_agent.return_value = mock_entry
        
        score = trust_manager.get_trust_score("new_agent")
        
        assert score == 100
        mock_score_manager.initialize_agent.assert_called_once_with("new_agent")
    
    def test_update_trust_score_existing_agent(self, trust_manager, mock_score_manager):
        """Test updating trust score for existing agent."""
        trust_manager.update_trust_score("test_agent", -15, "conflict penalty")
        
        mock_score_manager.adjust_score.assert_called_once_with("test_agent", -15, "conflict penalty")
    
    def test_update_trust_score_new_agent(self, trust_manager, mock_score_manager):
        """Test updating trust score for new agent (auto-initialization)."""
        # First call raises ValueError (agent not found)
        # Second call succeeds after initialization
        mock_score_manager.adjust_score.side_effect = [ValueError("Agent not found"), None]
        
        trust_manager.update_trust_score("new_agent", -10, "test penalty")
        
        # Should call initialize_agent and then adjust_score again
        mock_score_manager.initialize_agent.assert_called_once_with("new_agent")
        assert mock_score_manager.adjust_score.call_count == 2
    
    def test_check_quarantine_threshold_above(self, trust_manager, mock_score_manager):
        """Test quarantine check for agent above threshold."""
        mock_entry = TrustScoreEntry(
            agent_id="test_agent",
            current_score=50,  # Above threshold of 30
            last_updated=datetime.now(),
            adjustment_history=[],
            quarantine_count=0,
            creation_time=datetime.now()
        )
        mock_score_manager.get_score_entry.return_value = mock_entry
        
        should_quarantine = trust_manager.check_quarantine_threshold("test_agent")
        
        assert should_quarantine is False
    
    def test_check_quarantine_threshold_below(self, trust_manager, mock_score_manager):
        """Test quarantine check for agent below threshold."""
        mock_entry = TrustScoreEntry(
            agent_id="test_agent",
            current_score=25,  # Below threshold of 30
            last_updated=datetime.now(),
            adjustment_history=[],
            quarantine_count=0,
            creation_time=datetime.now()
        )
        mock_score_manager.get_score_entry.return_value = mock_entry
        
        should_quarantine = trust_manager.check_quarantine_threshold("test_agent")
        
        assert should_quarantine is True
    
    def test_get_agent_history(self, trust_manager, mock_score_manager):
        """Test getting agent adjustment history."""
        mock_history = [
            {"timestamp": "2024-01-01T10:00:00", "adjustment": -10, "reason": "conflict"}
        ]
        mock_entry = TrustScoreEntry(
            agent_id="test_agent",
            current_score=90,
            last_updated=datetime.now(),
            adjustment_history=mock_history,
            quarantine_count=0,
            creation_time=datetime.now()
        )
        mock_score_manager.get_score_entry.return_value = mock_entry
        
        history = trust_manager.get_agent_history("test_agent")
        
        assert history == mock_history
    
    def test_get_agent_history_not_found(self, trust_manager, mock_score_manager):
        """Test getting history for non-existent agent."""
        mock_score_manager.get_score_entry.return_value = None
        
        history = trust_manager.get_agent_history("nonexistent_agent")
        
        assert history == []
    
    def test_get_quarantine_count(self, trust_manager, mock_score_manager):
        """Test getting quarantine count for agent."""
        mock_entry = TrustScoreEntry(
            agent_id="test_agent",
            current_score=40,
            last_updated=datetime.now(),
            adjustment_history=[],
            quarantine_count=3,
            creation_time=datetime.now()
        )
        mock_score_manager.get_score_entry.return_value = mock_entry
        
        count = trust_manager.get_quarantine_count("test_agent")
        
        assert count == 3
    
    def test_get_quarantine_count_not_found(self, trust_manager, mock_score_manager):
        """Test getting quarantine count for non-existent agent."""
        mock_score_manager.get_score_entry.return_value = None
        
        count = trust_manager.get_quarantine_count("nonexistent_agent")
        
        assert count == 0