"""
Tests for the quarantine manager implementation.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from src.prediction_engine.quarantine_manager import RedisQuarantineManager
from src.prediction_engine.models.core import QuarantineResult
from src.prediction_engine.interfaces import AgentNetwork, Agent


class TestRedisQuarantineManager:
    """Test cases for the RedisQuarantineManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_redis_client = Mock()
        self.mock_agent_network = Mock(spec=AgentNetwork)
        
        self.manager = RedisQuarantineManager(
            redis_client_instance=self.mock_redis_client,
            key_prefix="test_quarantine"
        )
        self.manager.set_agent_network(self.mock_agent_network)
    
    def test_initialization(self):
        """Test quarantine manager initialization."""
        assert self.manager.redis_client == self.mock_redis_client
        assert self.manager.key_prefix == "test_quarantine"
        assert self.manager.agent_network == self.mock_agent_network
        assert isinstance(self.manager.quarantined_agents, set)
        assert isinstance(self.manager.quarantine_actions, list)
    
    def test_get_redis_keys(self):
        """Test Redis key generation."""
        agent_id = "agent_001"
        action_id = "action_123"
        
        status_key = self.manager._get_quarantine_key(agent_id)
        action_key = self.manager._get_action_key(action_id)
        agents_key = self.manager._get_agent_list_key()
        
        assert status_key == "test_quarantine:status:agent_001"
        assert action_key == "test_quarantine:action:action_123"
        assert agents_key == "test_quarantine:agents"
    
    def test_quarantine_agent_success(self):
        """Test successful agent quarantine."""
        agent_id = "agent_001"
        reason = "High conflict risk"
        
        # Mock Redis operations
        self.mock_redis_client.set_json.return_value = True
        self.mock_redis_client.set.return_value = True
        
        # Mock agent network
        mock_agent = Mock()
        mock_agent.agent_id = agent_id
        mock_agent.quarantine = Mock()
        self.mock_agent_network.get_active_agents.return_value = [mock_agent]
        
        result = self.manager.quarantine_agent(agent_id, reason)
        
        assert result.success is True
        assert result.agent_id == agent_id
        assert agent_id in self.manager.quarantined_agents
        assert len(self.manager.quarantine_actions) == 1
        
        # Verify Redis calls
        assert self.mock_redis_client.set_json.call_count == 2  # Status and action
        assert self.mock_redis_client.set.call_count == 1      # Agents list
        
        # Verify agent quarantine was enforced
        mock_agent.quarantine.assert_called_once()
    
    def test_quarantine_agent_already_quarantined(self):
        """Test quarantining an already quarantined agent."""
        agent_id = "agent_001"
        reason = "High conflict risk"
        
        # Pre-quarantine the agent
        self.manager.quarantined_agents.add(agent_id)
        
        result = self.manager.quarantine_agent(agent_id, reason)
        
        assert result.success is True
        assert "already quarantined" in result.reason
        
        # Should not make additional Redis calls
        self.mock_redis_client.set_json.assert_not_called()
    
    def test_quarantine_agent_redis_error(self):
        """Test quarantine with Redis error."""
        agent_id = "agent_001"
        reason = "High conflict risk"
        
        # Mock Redis error
        self.mock_redis_client.set_json.side_effect = Exception("Redis error")
        
        result = self.manager.quarantine_agent(agent_id, reason)
        
        assert result.success is False
        assert "Quarantine failed" in result.reason
        assert agent_id not in self.manager.quarantined_agents
    
    def test_is_quarantined_local_cache(self):
        """Test quarantine status check using local cache."""
        agent_id = "agent_001"
        
        # Add to local cache
        self.manager.quarantined_agents.add(agent_id)
        
        result = self.manager.is_quarantined(agent_id)
        
        assert result is True
        # Should not check Redis if in local cache
        self.mock_redis_client.get_json.assert_not_called()
    
    def test_is_quarantined_redis_check(self):
        """Test quarantine status check from Redis."""
        agent_id = "agent_001"
        
        # Mock Redis response
        self.mock_redis_client.get_json.return_value = {
            "agent_id": agent_id,
            "active": True,
            "reason": "Test quarantine"
        }
        
        result = self.manager.is_quarantined(agent_id)
        
        assert result is True
        assert agent_id in self.manager.quarantined_agents  # Should update cache
    
    def test_is_quarantined_not_quarantined(self):
        """Test quarantine status check for non-quarantined agent."""
        agent_id = "agent_001"
        
        # Mock Redis response (no data)
        self.mock_redis_client.get_json.return_value = None
        
        result = self.manager.is_quarantined(agent_id)
        
        assert result is False
        assert agent_id not in self.manager.quarantined_agents
    
    def test_release_quarantine_success(self):
        """Test successful quarantine release."""
        agent_id = "agent_001"
        
        # Pre-quarantine the agent
        self.manager.quarantined_agents.add(agent_id)
        
        # Mock Redis operations
        self.mock_redis_client.get_json.return_value = {
            "agent_id": agent_id,
            "active": True,
            "reason": "Test quarantine"
        }
        self.mock_redis_client.set_json.return_value = True
        self.mock_redis_client.set.return_value = True
        
        # Mock agent network
        mock_agent = Mock()
        mock_agent.agent_id = agent_id
        mock_agent.release_quarantine = Mock()
        self.mock_agent_network.agents = [mock_agent]  # Add agents attribute
        self.mock_agent_network.get_active_agents.return_value = [mock_agent]
        
        result = self.manager.release_quarantine(agent_id)
        
        assert result.success is True
        assert result.agent_id == agent_id
        assert agent_id not in self.manager.quarantined_agents
        
        # Verify agent quarantine was released
        mock_agent.release_quarantine.assert_called_once()
    
    def test_release_quarantine_not_quarantined(self):
        """Test releasing quarantine for non-quarantined agent."""
        agent_id = "agent_001"
        
        result = self.manager.release_quarantine(agent_id)
        
        assert result.success is True
        assert "was not quarantined" in result.reason
    
    def test_release_quarantine_redis_error(self):
        """Test quarantine release with Redis error."""
        agent_id = "agent_001"
        
        # Pre-quarantine the agent
        self.manager.quarantined_agents.add(agent_id)
        
        # Mock Redis error
        self.mock_redis_client.get_json.side_effect = Exception("Redis error")
        
        result = self.manager.release_quarantine(agent_id)
        
        assert result.success is False
        assert "Release failed" in result.reason
    
    def test_get_quarantined_agents(self):
        """Test getting list of quarantined agents."""
        agents = ["agent_001", "agent_002", "agent_003"]
        
        for agent_id in agents:
            self.manager.quarantined_agents.add(agent_id)
        
        result = self.manager.get_quarantined_agents()
        
        assert len(result) == 3
        assert all(agent_id in result for agent_id in agents)
    
    def test_get_quarantine_history_all(self):
        """Test getting complete quarantine history."""
        from src.prediction_engine.models.core import QuarantineAction
        
        actions = [
            QuarantineAction("agent_001", "reason1", datetime.now(), None, 80, 60),
            QuarantineAction("agent_002", "reason2", datetime.now(), None, 70, 50),
            QuarantineAction("agent_001", "reason3", datetime.now(), None, 60, 40)
        ]
        
        self.manager.quarantine_actions = actions
        
        result = self.manager.get_quarantine_history()
        
        assert len(result) == 3
        assert result == actions
    
    def test_get_quarantine_history_filtered(self):
        """Test getting quarantine history for specific agent."""
        from src.prediction_engine.models.core import QuarantineAction
        
        actions = [
            QuarantineAction("agent_001", "reason1", datetime.now(), None, 80, 60),
            QuarantineAction("agent_002", "reason2", datetime.now(), None, 70, 50),
            QuarantineAction("agent_001", "reason3", datetime.now(), None, 60, 40)
        ]
        
        self.manager.quarantine_actions = actions
        
        result = self.manager.get_quarantine_history("agent_001")
        
        assert len(result) == 2
        assert all(action.agent_id == "agent_001" for action in result)
    
    def test_get_statistics(self):
        """Test getting quarantine statistics."""
        from src.prediction_engine.models.core import QuarantineAction
        
        # Add quarantined agents
        self.manager.quarantined_agents.update(["agent_001", "agent_002"])
        
        # Add quarantine actions
        actions = [
            QuarantineAction("agent_001", "reason1", datetime.now(), None, 80, 60),
            QuarantineAction("agent_002", "reason2", datetime.now(), None, 70, 50),
            QuarantineAction("agent_001", "reason3", datetime.now(), None, 60, 40),
            QuarantineAction("agent_003", "reason4", datetime.now(), None, 90, 70)
        ]
        
        self.manager.quarantine_actions = actions
        
        stats = self.manager.get_statistics()
        
        assert stats["currently_quarantined"] == 2
        assert stats["total_quarantine_actions"] == 4
        assert stats["unique_agents_quarantined"] == 3  # agent_001, agent_002, agent_003
    
    def test_cleanup_expired_quarantines(self):
        """Test cleanup of expired quarantine records."""
        from src.prediction_engine.models.core import QuarantineAction
        
        now = datetime.now()
        old_time = now - timedelta(hours=25)  # Older than 24 hours
        recent_time = now - timedelta(hours=12)  # Within 24 hours
        
        actions = [
            QuarantineAction("agent_001", "old1", old_time, None, 80, 60),
            QuarantineAction("agent_002", "recent1", recent_time, None, 70, 50),
            QuarantineAction("agent_003", "old2", old_time, None, 60, 40),
            QuarantineAction("agent_004", "recent2", recent_time, None, 90, 70)
        ]
        
        self.manager.quarantine_actions = actions
        
        cleaned_count = self.manager.cleanup_expired_quarantines(max_age_hours=24)
        
        assert cleaned_count == 2  # Two old records removed
        assert len(self.manager.quarantine_actions) == 2
        
        # Verify only recent actions remain
        remaining_agents = [action.agent_id for action in self.manager.quarantine_actions]
        assert "agent_002" in remaining_agents
        assert "agent_004" in remaining_agents
        assert "agent_001" not in remaining_agents
        assert "agent_003" not in remaining_agents
    
    def test_enforce_quarantine_agent_not_found(self):
        """Test quarantine enforcement when agent is not found."""
        agent_id = "agent_001"
        
        # Mock empty agent list
        self.mock_agent_network.get_active_agents.return_value = []
        
        # This should not raise an exception
        self.manager._enforce_quarantine(agent_id)
        
        # No agent methods should be called
        self.mock_agent_network.get_active_agents.assert_called_once()
    
    def test_enforce_quarantine_no_network(self):
        """Test quarantine enforcement without agent network."""
        manager = RedisQuarantineManager(
            redis_client_instance=self.mock_redis_client
        )
        
        # This should not raise an exception
        manager._enforce_quarantine("agent_001")
    
    def test_load_quarantine_state_success(self):
        """Test loading quarantine state from Redis."""
        import json
        
        # Mock Redis response
        agents_data = json.dumps(["agent_001", "agent_002"])
        self.mock_redis_client.get.return_value = agents_data
        
        manager = RedisQuarantineManager(
            redis_client_instance=self.mock_redis_client
        )
        
        assert "agent_001" in manager.quarantined_agents
        assert "agent_002" in manager.quarantined_agents
        assert len(manager.quarantined_agents) == 2
    
    def test_load_quarantine_state_no_data(self):
        """Test loading quarantine state with no existing data."""
        # Mock Redis response (no data)
        self.mock_redis_client.get.return_value = None
        
        manager = RedisQuarantineManager(
            redis_client_instance=self.mock_redis_client
        )
        
        assert len(manager.quarantined_agents) == 0
    
    def test_load_quarantine_state_error(self):
        """Test loading quarantine state with Redis error."""
        # Mock Redis error
        self.mock_redis_client.get.side_effect = Exception("Redis error")
        
        manager = RedisQuarantineManager(
            redis_client_instance=self.mock_redis_client
        )
        
        # Should initialize with empty set on error
        assert len(manager.quarantined_agents) == 0