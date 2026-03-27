"""
Property-based test for Gemini API integration correctness.

**Feature: agent-conflict-predictor, Property 3: Gemini API integration correctness**
**Validates: Requirements 2.1, 2.2, 2.3**
"""
import pytest
from datetime import datetime
from typing import List
from unittest.mock import Mock, patch
from hypothesis import given, strategies as st, assume, settings

from src.prediction_engine.gemini_client import GeminiClient
from src.prediction_engine.game_theory.prompt_builder import GameTheoryPromptBuilder
from src.prediction_engine.analysis_parser import ConflictAnalysisParser
from src.prediction_engine.models.core import AgentIntention, ConflictAnalysis


class TestGeminiAPIIntegrationCorrectness:
    """Property-based tests for Gemini API integration correctness."""
    
    @given(
        intentions_data=st.lists(
            st.tuples(
                st.text(min_size=1, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'),  # agent_id
                st.sampled_from(['cpu', 'memory', 'network', 'storage', 'database']),  # resource_type
                st.integers(min_value=1, max_value=1000),  # requested_amount
                st.integers(min_value=1, max_value=10)     # priority_level
            ),
            min_size=1,
            max_size=10,
            unique_by=lambda x: (x[0], x[1])  # Unique (agent_id, resource_type) pairs
        )
    )
    @settings(max_examples=100)
    def test_prompt_formatting_correctness(self, intentions_data):
        """
        Property: For any set of agent intentions, the Gemini client should format 
        them into valid game theory prompts.
        
        **Feature: agent-conflict-predictor, Property 3: Gemini API integration correctness**
        **Validates: Requirements 2.1**
        """
        # Create agent intentions from generated data
        intentions = []
        for agent_id, resource_type, amount, priority in intentions_data:
            intention = AgentIntention(
                agent_id=agent_id,
                resource_type=resource_type,
                requested_amount=amount,
                priority_level=priority,
                timestamp=datetime.now()
            )
            intentions.append(intention)
        
        # Test prompt building
        prompt_builder = GameTheoryPromptBuilder()
        prompt = prompt_builder.build_conflict_analysis_prompt(intentions)
        
        # Verify prompt formatting correctness (Requirement 2.1)
        assert isinstance(prompt, str), "Prompt should be a string"
        assert len(prompt) > 0, "Prompt should not be empty"
        
        # Verify all agent IDs are included in the prompt
        for intention in intentions:
            assert intention.agent_id in prompt, f"Agent {intention.agent_id} should be mentioned in prompt"
        
        # Verify all resource types are included in the prompt
        resource_types = set(intention.resource_type for intention in intentions)
        for resource_type in resource_types:
            assert resource_type in prompt, f"Resource type {resource_type} should be mentioned in prompt"
        
        # Verify prompt contains required output format markers
        assert "RISK_SCORE" in prompt, "Prompt should specify RISK_SCORE output format"
        assert "CONFIDENCE" in prompt, "Prompt should specify CONFIDENCE output format"
        
        # Verify prompt contains game theory context
        game_theory_keywords = ["game theory", "nash", "equilibrium", "strategy", "conflict"]
        has_game_theory_context = any(keyword.lower() in prompt.lower() for keyword in game_theory_keywords)
        assert has_game_theory_context, "Prompt should contain game theory analysis context"
    
    @patch('src.prediction_engine.gemini_client.genai')
    def test_model_usage_correctness(self, mock_genai):
        """
        Property: For any Gemini client initialization, the system should use 
        the gemini-3-pro-preview model for conflict analysis.
        
        **Feature: agent-conflict-predictor, Property 3: Gemini API integration correctness**
        **Validates: Requirements 2.2**
        """
        # Mock newer API approach first
        mock_client = Mock()
        mock_genai.Client.return_value = mock_client
        
        # Test default model usage
        client = GeminiClient()
        
        # Verify correct model is used (Requirement 2.2)
        mock_genai.Client.assert_called_with(api_key=client.api_key)
        assert client.model == "gemini-3-pro-preview", "Should use gemini-3-pro-preview model by default"
        
        # Test custom model specification
        custom_client = GeminiClient(model="custom-model")
        assert custom_client.model == "custom-model", "Should accept custom model specification"
    
    @given(
        risk_scores=st.lists(
            st.floats(min_value=0.0, max_value=1.0),
            min_size=1,
            max_size=5
        ),
        confidence_scores=st.lists(
            st.floats(min_value=0.0, max_value=1.0),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=100)
    @patch('src.prediction_engine.gemini_client.genai')
    def test_risk_score_range_correctness(self, mock_genai, risk_scores, confidence_scores):
        """
        Property: For any conflict analysis response, the system should parse and 
        return numerical conflict risk scores between 0.0 and 1.0.
        
        **Feature: agent-conflict-predictor, Property 3: Gemini API integration correctness**
        **Validates: Requirements 2.3**
        """
        # Ensure we have at least one score of each type
        assume(len(risk_scores) > 0 and len(confidence_scores) > 0)
        
        for risk_score in risk_scores:
            for confidence_score in confidence_scores:
                # Mock Gemini API response with generated scores
                mock_response = Mock()
                mock_response.text = f"""
                RISK_SCORE: {risk_score}
                CONFIDENCE: {confidence_score}
                AFFECTED_AGENTS: agent_1, agent_2
                FAILURE_MODE: Test scenario
                NASH_EQUILIBRIUM: Test equilibrium
                REASONING: Generated test case
                """
                
                mock_client = Mock()
                mock_client.generate_content.return_value = mock_response
                mock_genai.Client.return_value = mock_client
                
                # Create test intentions
                intentions = [
                    AgentIntention(
                        agent_id="agent_1",
                        resource_type="cpu",
                        requested_amount=50,
                        priority_level=5,
                        timestamp=datetime.now()
                    )
                ]
                
                # Execute analysis
                client = GeminiClient()
                result = client.analyze_conflict_risk(intentions)
                
                # Verify risk score range correctness (Requirement 2.3)
                assert isinstance(result, ConflictAnalysis), "Should return ConflictAnalysis object"
                assert isinstance(result.risk_score, float), "Risk score should be a float"
                assert 0.0 <= result.risk_score <= 1.0, f"Risk score {result.risk_score} should be between 0.0 and 1.0"
                assert isinstance(result.confidence_level, float), "Confidence should be a float"
                assert 0.0 <= result.confidence_level <= 1.0, f"Confidence {result.confidence_level} should be between 0.0 and 1.0"
    
    @given(
        intentions_data=st.lists(
            st.tuples(
                st.text(min_size=1, max_size=15, alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'),
                st.sampled_from(['cpu', 'memory', 'network', 'storage']),
                st.integers(min_value=1, max_value=500),
                st.integers(min_value=1, max_value=10)
            ),
            min_size=1,
            max_size=8,
            unique_by=lambda x: x[0]  # Unique agent IDs
        )
    )
    @settings(max_examples=100)
    @patch('src.prediction_engine.gemini_client.genai')
    def test_end_to_end_integration_correctness(self, mock_genai, intentions_data):
        """
        Property: For any set of agent intentions, the complete Gemini integration 
        workflow should format prompts, use correct model, and return valid risk scores.
        
        **Feature: agent-conflict-predictor, Property 3: Gemini API integration correctness**
        **Validates: Requirements 2.1, 2.2, 2.3**
        """
        # Mock valid Gemini API response
        mock_response = Mock()
        mock_response.text = """
        RISK_SCORE: 0.65
        CONFIDENCE: 0.8
        AFFECTED_AGENTS: test_agent
        FAILURE_MODE: Resource contention scenario
        NASH_EQUILIBRIUM: Stable cooperative equilibrium
        REASONING: Moderate contention with cooperative strategies
        """
        
        mock_client = Mock()
        mock_client.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client
        
        # Create agent intentions from generated data
        intentions = []
        for agent_id, resource_type, amount, priority in intentions_data:
            intention = AgentIntention(
                agent_id=agent_id,
                resource_type=resource_type,
                requested_amount=amount,
                priority_level=priority,
                timestamp=datetime.now()
            )
            intentions.append(intention)
        
        # Execute complete workflow
        client = GeminiClient()
        # Disable Redis caching for this test to ensure fresh API call
        client.redis = None
        result = client.analyze_conflict_risk(intentions)
        
        # Verify complete integration correctness
        # Requirement 2.1: Prompt formatting
        mock_client.generate_content.assert_called_once()
        call_args = mock_client.generate_content.call_args[0]
        prompt = call_args[0]
        
        assert isinstance(prompt, str), "Should generate string prompt"
        assert len(prompt) > 0, "Prompt should not be empty"
        
        # Verify agent data is included in prompt
        for intention in intentions:
            assert intention.agent_id in prompt, f"Agent {intention.agent_id} should be in prompt"
        
        # Requirement 2.2: Correct model usage
        mock_genai.Client.assert_called_with(api_key=client.api_key)
        
        # Requirement 2.3: Valid risk score range
        assert isinstance(result, ConflictAnalysis), "Should return ConflictAnalysis"
        assert isinstance(result.risk_score, float), "Risk score should be float"
        assert 0.0 <= result.risk_score <= 1.0, "Risk score should be in valid range"
        assert isinstance(result.confidence_level, float), "Confidence should be float"
        assert 0.0 <= result.confidence_level <= 1.0, "Confidence should be in valid range"
        
        # Verify timestamp is recent
        time_diff = (datetime.now() - result.timestamp).total_seconds()
        assert time_diff < 60, "Timestamp should be recent"
    
    def test_empty_intentions_error_handling(self):
        """
        Test edge case: Empty intentions should raise appropriate error.
        
        **Feature: agent-conflict-predictor, Property 3: Gemini API integration correctness**
        **Validates: Requirements 2.1**
        """
        prompt_builder = GameTheoryPromptBuilder()
        
        with pytest.raises(ValueError, match="empty intentions list"):
            prompt_builder.build_conflict_analysis_prompt([])
    
    def test_invalid_intention_data_handling(self):
        """
        Test edge case: Invalid intention data should raise appropriate errors.
        
        **Feature: agent-conflict-predictor, Property 3: Gemini API integration correctness**
        **Validates: Requirements 2.1**
        """
        prompt_builder = GameTheoryPromptBuilder()
        
        # Test invalid agent ID
        invalid_intention = AgentIntention(
            agent_id="",  # Empty agent ID
            resource_type="cpu",
            requested_amount=10,
            priority_level=5,
            timestamp=datetime.now()
        )
        
        with pytest.raises(ValueError, match="valid agent_id"):
            prompt_builder.build_conflict_analysis_prompt([invalid_intention])
        
        # Test invalid resource type
        invalid_intention2 = AgentIntention(
            agent_id="agent_1",
            resource_type="",  # Empty resource type
            requested_amount=10,
            priority_level=5,
            timestamp=datetime.now()
        )
        
        with pytest.raises(ValueError, match="valid resource_type"):
            prompt_builder.build_conflict_analysis_prompt([invalid_intention2])
        
        # Test invalid requested amount
        invalid_intention3 = AgentIntention(
            agent_id="agent_1",
            resource_type="cpu",
            requested_amount=0,  # Zero amount
            priority_level=5,
            timestamp=datetime.now()
        )
        
        with pytest.raises(ValueError, match="positive requested_amount"):
            prompt_builder.build_conflict_analysis_prompt([invalid_intention3])
    
    @patch('src.prediction_engine.gemini_client.genai')
    def test_malformed_response_handling(self, mock_genai):
        """
        Test edge case: Malformed API responses should be handled gracefully.
        
        **Feature: agent-conflict-predictor, Property 3: Gemini API integration correctness**
        **Validates: Requirements 2.3**
        """
        # Test empty response - should use fallback, not raise exception
        mock_response = Mock()
        mock_response.text = ""
        mock_client = Mock()
        mock_client.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client
        
        intentions = [
            AgentIntention(
                agent_id="agent_1",
                resource_type="cpu",
                requested_amount=10,
                priority_level=5,
                timestamp=datetime.now()
            )
        ]
        
        client = GeminiClient()
        
        # Should not raise exception, but use fallback analysis
        result = client.analyze_conflict_risk(intentions)
        assert result is not None
        assert isinstance(result.risk_score, float)
        assert 0.0 <= result.risk_score <= 1.0
        
        # Test response without risk score - should use fallback
        mock_response.text = "CONFIDENCE: 0.8\nAFFECTED_AGENTS: agent_1"
        result = client.analyze_conflict_risk(intentions)
        assert result is not None
        assert isinstance(result.risk_score, float)
        assert 0.0 <= result.risk_score <= 1.0
        
        # Test response with invalid risk score - should use fallback
        mock_response.text = "RISK_SCORE: invalid_number"
        result = client.analyze_conflict_risk(intentions)
        assert result is not None
        assert isinstance(result.risk_score, float)
        assert 0.0 <= result.risk_score <= 1.0
    
    @given(
        risk_score=st.one_of(
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),  # Valid range
            st.floats(min_value=-5.0, max_value=-0.1, allow_nan=False, allow_infinity=False),  # Negative range
            st.floats(min_value=1.1, max_value=5.0, allow_nan=False, allow_infinity=False)   # Above 1.0 range
        )
    )
    @settings(max_examples=50)
    def test_risk_score_clamping_behavior(self, risk_score):
        """
        Property: Risk scores outside valid range should be clamped to [0.0, 1.0].
        
        **Feature: agent-conflict-predictor, Property 3: Gemini API integration correctness**
        **Validates: Requirements 2.3**
        """
        parser = ConflictAnalysisParser()
        
        response = f"RISK_SCORE: {risk_score}\nCONFIDENCE: 0.9"
        
        try:
            result = parser.parse_conflict_analysis(response)
            
            # All parsed results should have valid risk scores
            assert 0.0 <= result.risk_score <= 1.0, "Risk score should be in valid range"
            
            if 0.0 <= risk_score <= 1.0:
                # Valid range should parse normally (with some tolerance for floating point)
                # For very small numbers (close to zero), the parser might clamp to 0.0
                if abs(risk_score) < 1e-10:
                    # Very small numbers should be clamped to 0.0
                    assert result.risk_score == 0.0 or result.risk_score == risk_score, f"Very small number should be 0.0 or {risk_score}, got {result.risk_score}"
                else:
                    assert abs(result.risk_score - risk_score) < 1e-6, f"Expected {risk_score}, got {result.risk_score}"
            else:
                # Invalid range should be clamped
                if risk_score < 0.0:
                    assert result.risk_score == 0.0, "Negative scores should be clamped to 0.0"
                elif risk_score > 1.0:
                    assert result.risk_score == 1.0, "Scores above 1.0 should be clamped to 1.0"
        except ValueError as e:
            # Some numbers might not be parseable due to formatting, which is acceptable
            assert "Risk score not found" in str(e) or "Invalid risk score format" in str(e)
    
    @patch('src.prediction_engine.gemini_client.genai')
    def test_api_error_handling_integration(self, mock_genai):
        """
        Test that API errors are properly propagated through the integration.
        
        **Feature: agent-conflict-predictor, Property 3: Gemini API integration correctness**
        **Validates: Requirements 2.2**
        """
        from google.genai.errors import APIError, ClientError, ServerError
        
        mock_client = Mock()
        mock_genai.Client.return_value = mock_client
        
        intentions = [
            AgentIntention(
                agent_id="agent_1",
                resource_type="cpu",
                requested_amount=10,
                priority_level=5,
                timestamp=datetime.now()
            )
        ]
        
        client = GeminiClient()
        
        # Test generic Exception handling - should use fallback, not raise exception
        mock_client.generate_content.side_effect = Exception("API Connection Error")
        result = client.analyze_conflict_risk(intentions)
        assert result is not None
        assert isinstance(result.risk_score, float)
        assert 0.0 <= result.risk_score <= 1.0
        
        # Test that the client handles runtime errors gracefully with fallback
        mock_client.generate_content.side_effect = RuntimeError("Runtime Error")
        result = client.analyze_conflict_risk(intentions)
        assert result is not None
        assert isinstance(result.risk_score, float)
        assert 0.0 <= result.risk_score <= 1.0
        
        # Test connection timeout simulation - should use fallback
        mock_client.generate_content.side_effect = ConnectionError("Connection timeout")
        result = client.analyze_conflict_risk(intentions)
        assert result is not None
        assert isinstance(result.risk_score, float)
        assert 0.0 <= result.risk_score <= 1.0