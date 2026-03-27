"""
Basic integration test for Gemini API components.
"""
import pytest
from unittest.mock import Mock, patch, PropertyMock
from datetime import datetime
from src.prediction_engine.gemini_client import GeminiClient
from src.prediction_engine.models.core import AgentIntention, GameState


class TestGeminiIntegration:
    """Integration tests for Gemini API components."""
    
    @patch('src.prediction_engine.gemini_client.genai')
    @patch('src.prediction_engine.gemini_client.RedisClient')
    def test_full_conflict_analysis_workflow(self, mock_redis_cls, mock_genai):
        """Test complete workflow from intentions to conflict analysis."""
        # Mock Redis
        mock_redis = Mock()
        mock_redis.get.return_value = None
        mock_redis_cls.return_value = mock_redis
        
        # Mock Gemini API response
        mock_response = Mock()
        type(mock_response).text = PropertyMock(return_value="""
        RISK_SCORE: 0.8
        CONFIDENCE: 0.9
        AFFECTED_AGENTS: agent_1, agent_2
        FAILURE_MODE: CPU resource deadlock
        NASH_EQUILIBRIUM: Competitive equilibrium with high contention
        REASONING: Both agents requesting high-priority CPU access creates deadlock risk
        """)
    
        # Mock the newer API approach
        mock_client = Mock()
        mock_client.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client
        
        # Create test data
        intentions = [
            AgentIntention(
                agent_id="agent_1",
                resource_type="cpu",
                requested_amount=50,
                priority_level=9,
                timestamp=datetime.now()
            ),
            AgentIntention(
                agent_id="agent_2",
                resource_type="cpu",
                requested_amount=60,
                priority_level=8,
                timestamp=datetime.now()
            )
        ]
        
        # Execute workflow
        client = GeminiClient()
        result = client.analyze_conflict_risk(intentions)
        
        # Verify results
        assert result.risk_score == 0.8
        assert result.confidence_level == 0.9
        assert "agent_1" in result.affected_agents
        assert "agent_2" in result.affected_agents
        assert "deadlock" in result.predicted_failure_mode.lower()
        
        # Verify API was called with proper prompt
        mock_client.generate_content.assert_called_once()
        call_args = mock_client.generate_content.call_args[0]
        prompt = call_args[0]
        
        # Verify prompt contains expected elements
        assert "agent_1" in prompt
        assert "agent_2" in prompt
        assert "cpu" in prompt
        assert "RISK_SCORE" in prompt
    
    @patch('src.prediction_engine.gemini_client.genai')
    def test_full_equilibrium_analysis_workflow(self, mock_genai):
        """Test complete workflow from game state to equilibrium analysis."""
        # Mock Gemini API response
        mock_response = Mock()
        mock_response.text = """
        STRATEGY_PROFILE: agent_1:cooperate, agent_2:compete
        PAYOFFS: agent_1:0.6, agent_2:0.4
        STABILITY_SCORE: 0.75
        EQUILIBRIUM_TYPE: mixed
        REASONING: Mixed equilibrium with cooperation bias
        """
        
        # Mock the newer API approach
        mock_client = Mock()
        mock_client.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client
        
        # Create test data
        game_state = GameState(
            agents=["agent_1", "agent_2"],
            resources={"cpu": 100, "memory": 200},
            intentions=[
                AgentIntention(
                    agent_id="agent_1",
                    resource_type="cpu",
                    requested_amount=30,
                    priority_level=5,
                    timestamp=datetime.now()
                )
            ],
            timestamp=datetime.now()
        )
        
        # Execute workflow
        client = GeminiClient()
        result = client.calculate_nash_equilibrium(game_state)
        
        # Verify results
        assert result.stability_score == 0.75
        assert result.strategy_profile["agent_1"] == "cooperate"
        assert result.strategy_profile["agent_2"] == "compete"
        assert result.payoffs["agent_1"] == 0.6
        assert result.payoffs["agent_2"] == 0.4
        
        # Verify API was called with proper prompt
        mock_client.generate_content.assert_called_once()
        call_args = mock_client.generate_content.call_args[0]
        prompt = call_args[0]
        
        # Verify prompt contains expected elements
        assert "agent_1" in prompt
        assert "agent_2" in prompt
        assert "STRATEGY_PROFILE" in prompt