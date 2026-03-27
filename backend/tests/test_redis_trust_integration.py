"""
Integration tests for Redis trust management system.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.prediction_engine.trust_manager import RedisTrustManager, RedisTrustScoreManager
from src.prediction_engine.redis_client import RedisClient


class TestRedisTrustIntegration:
    """Integration tests for Redis trust management system."""
    
    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client that simulates Redis behavior."""
        mock_client = Mock()
        
        # Simulate Redis storage
        self.redis_storage = {}
        
        def mock_exists(key):
            return key in self.redis_storage
        
        def mock_get_json(key):
            return self.redis_storage.get(key)
        
        def mock_set_json(key, value, ttl=None):
            self.redis_storage[key] = value
            return True
        
        mock_client.exists.side_effect = mock_exists
        mock_client.get_json.side_effect = mock_get_json
        mock_client.set_json.side_effect = mock_set_json
        
        return mock_client
    
    def test_full_trust_management_workflow(self, mock_redis_client):
        """Test complete trust management workflow from initialization to quarantine check."""
        # Create trust manager with mock Redis client
        score_manager = RedisTrustScoreManager(redis_client_instance=mock_redis_client)
        trust_manager = RedisTrustManager(score_manager=score_manager)
        
        agent_id = "test_agent_001"
        
        # Step 1: Get trust score for new agent (should auto-initialize)
        initial_score = trust_manager.get_trust_score(agent_id)
        assert initial_score == 100
        
        # Verify agent was initialized in Redis
        assert f"trust_score:{agent_id}" in self.redis_storage
        entry_data = self.redis_storage[f"trust_score:{agent_id}"]
        assert entry_data["agent_id"] == agent_id
        assert entry_data["current_score"] == 100
        assert entry_data["quarantine_count"] == 0
        
        # Step 2: Apply some trust score adjustments
        trust_manager.update_trust_score(agent_id, -15, "conflict detected")
        trust_manager.update_trust_score(agent_id, -10, "timeout occurred")
        trust_manager.update_trust_score(agent_id, 5, "successful cooperation")
        
        # Check updated score
        current_score = trust_manager.get_trust_score(agent_id)
        assert current_score == 80  # 100 - 15 - 10 + 5
        
        # Step 3: Check quarantine threshold (should not be quarantined yet)
        should_quarantine = trust_manager.check_quarantine_threshold(agent_id)
        assert should_quarantine is False
        
        # Step 4: Apply large penalty to trigger quarantine threshold
        trust_manager.update_trust_score(agent_id, -55, "major violation")
        
        # Check score and quarantine status
        final_score = trust_manager.get_trust_score(agent_id)
        assert final_score == 25  # 80 - 55
        
        should_quarantine = trust_manager.check_quarantine_threshold(agent_id)
        assert should_quarantine is True  # Below threshold of 30
        
        # Step 5: Verify adjustment history
        history = trust_manager.get_agent_history(agent_id)
        assert len(history) == 4  # Four adjustments made
        
        # Verify history details
        assert history[0]["adjustment"] == -15
        assert history[0]["reason"] == "conflict detected"
        assert history[1]["adjustment"] == -10
        assert history[1]["reason"] == "timeout occurred"
        assert history[2]["adjustment"] == 5
        assert history[2]["reason"] == "successful cooperation"
        assert history[3]["adjustment"] == -55
        assert history[3]["reason"] == "major violation"
        
        # Step 6: Verify quarantine count
        quarantine_count = trust_manager.get_quarantine_count(agent_id)
        assert quarantine_count == 0  # No quarantine-specific adjustments yet
    
    def test_multiple_agents_management(self, mock_redis_client):
        """Test managing trust scores for multiple agents."""
        score_manager = RedisTrustScoreManager(redis_client_instance=mock_redis_client)
        trust_manager = RedisTrustManager(score_manager=score_manager)
        
        agents = ["agent_001", "agent_002", "agent_003"]
        
        # Initialize all agents
        for agent_id in agents:
            score = trust_manager.get_trust_score(agent_id)
            assert score == 100
        
        # Apply different adjustments to each agent
        trust_manager.update_trust_score("agent_001", -20, "minor conflict")
        trust_manager.update_trust_score("agent_002", -40, "major conflict")
        trust_manager.update_trust_score("agent_003", -60, "severe violation")
        
        # Check individual scores
        assert trust_manager.get_trust_score("agent_001") == 80
        assert trust_manager.get_trust_score("agent_002") == 60
        assert trust_manager.get_trust_score("agent_003") == 40
        
        # Check quarantine status
        assert trust_manager.check_quarantine_threshold("agent_001") is False  # 80 > 30
        assert trust_manager.check_quarantine_threshold("agent_002") is False  # 60 > 30
        assert trust_manager.check_quarantine_threshold("agent_003") is False  # 40 > 30
        
        # Push agent_003 below threshold
        trust_manager.update_trust_score("agent_003", -15, "additional violation")
        assert trust_manager.get_trust_score("agent_003") == 25
        assert trust_manager.check_quarantine_threshold("agent_003") is True  # 25 < 30
        
        # Verify other agents unaffected
        assert trust_manager.get_trust_score("agent_001") == 80
        assert trust_manager.get_trust_score("agent_002") == 60
    
    def test_trust_score_bounds_enforcement(self, mock_redis_client):
        """Test that trust scores are properly bounded between 0 and 100."""
        score_manager = RedisTrustScoreManager(redis_client_instance=mock_redis_client)
        trust_manager = RedisTrustManager(score_manager=score_manager)
        
        agent_id = "bounds_test_agent"
        
        # Initialize agent
        initial_score = trust_manager.get_trust_score(agent_id)
        assert initial_score == 100
        
        # Try to exceed upper bound
        trust_manager.update_trust_score(agent_id, 50, "bonus points")
        score = trust_manager.get_trust_score(agent_id)
        assert score == 100  # Should be clamped to maximum
        
        # Reduce to middle range
        trust_manager.update_trust_score(agent_id, -50, "penalty")
        score = trust_manager.get_trust_score(agent_id)
        assert score == 50
        
        # Try to go below lower bound
        trust_manager.update_trust_score(agent_id, -100, "severe penalty")
        score = trust_manager.get_trust_score(agent_id)
        assert score == 0  # Should be clamped to minimum
        
        # Try to go further below (should stay at 0)
        trust_manager.update_trust_score(agent_id, -50, "additional penalty")
        score = trust_manager.get_trust_score(agent_id)
        assert score == 0  # Should remain at minimum
    
    def test_quarantine_tracking(self, mock_redis_client):
        """Test quarantine count tracking in trust score adjustments."""
        score_manager = RedisTrustScoreManager(redis_client_instance=mock_redis_client)
        trust_manager = RedisTrustManager(score_manager=score_manager)
        
        agent_id = "quarantine_test_agent"
        
        # Initialize agent
        trust_manager.get_trust_score(agent_id)
        
        # Apply non-quarantine adjustments
        trust_manager.update_trust_score(agent_id, -10, "minor issue")
        trust_manager.update_trust_score(agent_id, -5, "timeout")
        
        # Check quarantine count (should be 0)
        quarantine_count = trust_manager.get_quarantine_count(agent_id)
        assert quarantine_count == 0
        
        # Apply quarantine-related adjustments
        trust_manager.update_trust_score(agent_id, -20, "quarantine penalty")
        trust_manager.update_trust_score(agent_id, -15, "post-quarantine adjustment")
        
        # Check quarantine count (should be 2 since both contain "quarantine")
        quarantine_count = trust_manager.get_quarantine_count(agent_id)
        assert quarantine_count == 2
        
        # Apply another quarantine adjustment
        trust_manager.update_trust_score(agent_id, -10, "second quarantine event")
        
        # Check quarantine count (should be 3)
        quarantine_count = trust_manager.get_quarantine_count(agent_id)
        assert quarantine_count == 3