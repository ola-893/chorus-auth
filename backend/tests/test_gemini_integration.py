"""
Tests for Gemini API integration components.
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from src.prediction_engine.gemini_client import GeminiClient
from src.prediction_engine.game_theory.prompt_builder import GameTheoryPromptBuilder
from src.prediction_engine.analysis_parser import ConflictAnalysisParser
from src.prediction_engine.models.core import AgentIntention, GameState, ConflictAnalysis


class TestGeminiClient:
    """Test cases for GeminiClient."""
    
    def test_initialization_with_defaults(self):
        """Test GeminiClient initialization with default settings."""
        with patch('src.prediction_engine.gemini_client.genai') as mock_genai:
            # Mock the newer API approach
            mock_client = Mock()
            mock_genai.Client.return_value = mock_client
            
            client = GeminiClient()
            
            assert client.api_key is not None
            assert client.model == "gemini-3-pro-preview"
            assert client.prompt_builder is not None
            assert client.parser is not None
            mock_genai.Client.assert_called_once()
    
    def test_initialization_with_custom_params(self):
        """Test GeminiClient initialization with custom parameters."""
        with patch('src.prediction_engine.gemini_client.genai') as mock_genai:
            # Mock the newer API approach
            mock_client = Mock()
            mock_genai.Client.return_value = mock_client
            
            client = GeminiClient(api_key="test_key", model="test_model")
            
            assert client.api_key == "test_key"
            assert client.model == "test_model"
            mock_genai.Client.assert_called_once_with(api_key="test_key")
    
    def test_connection_test_success(self):
        """Test successful connection test."""
        with patch('src.prediction_engine.gemini_client.genai') as mock_genai:
            mock_client = Mock()
            # Mock the newer API approach - models.list()
            mock_models = Mock()
            mock_models.list.return_value = iter(['model1', 'model2'])
            mock_client.models = mock_models
            mock_genai.Client.return_value = mock_client
            
            client = GeminiClient()
            result = client.test_connection()
            
            assert result is True
    
    def test_connection_test_failure(self):
        """Test connection test failure."""
        with patch('src.prediction_engine.gemini_client.genai') as mock_genai:
            mock_client = Mock()
            # Mock failure - remove models attribute to simulate failure
            mock_client.configure_mock(**{'models': None})
            # Also remove generate_content to ensure it goes to the failure path
            del mock_client.generate_content
            mock_genai.Client.return_value = mock_client
            
            client = GeminiClient()
            result = client.test_connection()
            
            assert result is False


class TestGameTheoryPromptBuilder:
    """Test cases for GameTheoryPromptBuilder."""
    
    def test_initialization(self):
        """Test prompt builder initialization."""
        builder = GameTheoryPromptBuilder()
        assert builder.conflict_template is not None
        assert builder.equilibrium_template is not None
    
    def test_build_conflict_analysis_prompt_valid_input(self):
        """Test building conflict analysis prompt with valid input."""
        builder = GameTheoryPromptBuilder()
        
        intentions = [
            AgentIntention(
                agent_id="agent_1",
                resource_type="cpu",
                requested_amount=10,
                priority_level=5,
                timestamp=datetime.now()
            ),
            AgentIntention(
                agent_id="agent_2",
                resource_type="cpu",
                requested_amount=15,
                priority_level=8,
                timestamp=datetime.now()
            )
        ]
        
        prompt = builder.build_conflict_analysis_prompt(intentions)
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "agent_1" in prompt
        assert "agent_2" in prompt
        assert "cpu" in prompt
        assert "RISK_SCORE" in prompt
    
    def test_build_conflict_analysis_prompt_empty_input(self):
        """Test building conflict analysis prompt with empty input."""
        builder = GameTheoryPromptBuilder()
        
        with pytest.raises(ValueError, match="empty intentions list"):
            builder.build_conflict_analysis_prompt([])
    
    def test_build_nash_equilibrium_prompt_valid_input(self):
        """Test building Nash equilibrium prompt with valid input."""
        builder = GameTheoryPromptBuilder()
        
        game_state = GameState(
            agents=["agent_1", "agent_2"],
            resources={"cpu": 100, "memory": 200},
            intentions=[
                AgentIntention(
                    agent_id="agent_1",
                    resource_type="cpu",
                    requested_amount=10,
                    priority_level=5,
                    timestamp=datetime.now()
                )
            ],
            timestamp=datetime.now()
        )
        
        prompt = builder.build_nash_equilibrium_prompt(game_state)
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "agent_1" in prompt
        assert "agent_2" in prompt
        assert "STRATEGY_PROFILE" in prompt


class TestConflictAnalysisParser:
    """Test cases for ConflictAnalysisParser."""
    
    def test_initialization(self):
        """Test parser initialization."""
        parser = ConflictAnalysisParser()
        assert parser.risk_score_pattern is not None
        assert parser.confidence_pattern is not None
    
    def test_parse_conflict_analysis_valid_response(self):
        """Test parsing valid conflict analysis response."""
        parser = ConflictAnalysisParser()
        
        response = """
        RISK_SCORE: 0.75
        CONFIDENCE: 0.85
        AFFECTED_AGENTS: agent_1, agent_2
        FAILURE_MODE: Resource deadlock detected
        NASH_EQUILIBRIUM: Competitive equilibrium
        """
        
        result = parser.parse_conflict_analysis(response)
        
        assert isinstance(result, ConflictAnalysis)
        assert result.risk_score == 0.75
        assert result.confidence_level == 0.85
        assert "agent_1" in result.affected_agents
        assert "agent_2" in result.affected_agents
        assert "deadlock" in result.predicted_failure_mode.lower()
    
    def test_parse_conflict_analysis_minimal_response(self):
        """Test parsing minimal valid conflict analysis response."""
        parser = ConflictAnalysisParser()
        
        response = "RISK_SCORE: 0.5"
        
        result = parser.parse_conflict_analysis(response)
        
        assert isinstance(result, ConflictAnalysis)
        assert result.risk_score == 0.5
        assert result.confidence_level == 0.5  # Default value
    
    def test_parse_conflict_analysis_empty_response(self):
        """Test parsing empty response."""
        parser = ConflictAnalysisParser()
        
        with pytest.raises(ValueError, match="empty"):
            parser.parse_conflict_analysis("")
    
    def test_parse_conflict_analysis_invalid_risk_score(self):
        """Test parsing response with invalid risk score."""
        parser = ConflictAnalysisParser()
        
        response = "RISK_SCORE: invalid"
        
        with pytest.raises(ValueError):
            parser.parse_conflict_analysis(response)
    
    def test_validate_response_format_conflict(self):
        """Test response format validation for conflict analysis."""
        parser = ConflictAnalysisParser()
        
        valid_response = "RISK_SCORE: 0.5"
        invalid_response = "No risk score here"
        
        assert parser.validate_response_format(valid_response, "conflict") is True
        assert parser.validate_response_format(invalid_response, "conflict") is False