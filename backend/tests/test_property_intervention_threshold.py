"""
Property-based test for intervention threshold accuracy.

**Feature: agent-conflict-predictor, Property 5: Intervention threshold accuracy**
**Validates: Requirements 2.5, 4.1**
"""
import pytest
from datetime import datetime
from typing import List
from unittest.mock import Mock, patch
from hypothesis import given, strategies as st, assume, settings

from src.prediction_engine.gemini_client import GeminiClient
from src.prediction_engine.models.core import AgentIntention, ConflictAnalysis


class InterventionLogic:
    """
    Simple intervention logic to test the threshold accuracy property.
    
    This represents the core logic that should be implemented in the 
    InterventionEngine for determining when intervention is needed.
    """
    
    HIGH_RISK_THRESHOLD = 0.7
    
    @classmethod
    def should_intervene(cls, conflict_analysis: ConflictAnalysis) -> bool:
        """
        Determine if intervention is needed based on conflict analysis.
        
        Args:
            conflict_analysis: The conflict analysis result from Gemini API.
            
        Returns:
            True if intervention is needed (high-risk situation).
        """
        return conflict_analysis.risk_score > cls.HIGH_RISK_THRESHOLD
    
    @classmethod
    def classify_risk_level(cls, risk_score: float) -> str:
        """
        Classify risk level based on score.
        
        Args:
            risk_score: Risk score between 0.0 and 1.0.
            
        Returns:
            Risk level classification.
        """
        if risk_score > cls.HIGH_RISK_THRESHOLD:
            return "high-risk"
        elif risk_score > 0.4:
            return "medium-risk"
        else:
            return "low-risk"
    
    @classmethod
    def identify_most_aggressive_agent(cls, intentions: List[AgentIntention]) -> str:
        """
        Identify the most aggressive agent based on intentions.
        
        Args:
            intentions: List of agent intentions to analyze.
            
        Returns:
            Agent ID of the most aggressive agent.
        """
        if not intentions:
            raise ValueError("Cannot identify aggressive agent from empty intentions")
        
        # Calculate aggressiveness score for each agent
        agent_scores = {}
        for intention in intentions:
            agent_id = intention.agent_id
            if agent_id not in agent_scores:
                agent_scores[agent_id] = {
                    'total_demand': 0,
                    'max_priority': 0,
                    'request_count': 0
                }
            
            agent_scores[agent_id]['total_demand'] += intention.requested_amount
            agent_scores[agent_id]['max_priority'] = max(
                agent_scores[agent_id]['max_priority'], 
                intention.priority_level
            )
            agent_scores[agent_id]['request_count'] += 1
        
        # Calculate composite aggressiveness score
        most_aggressive = None
        highest_score = -1
        
        for agent_id, scores in agent_scores.items():
            # Composite score: priority weight + demand weight + frequency weight
            composite_score = (
                scores['max_priority'] * 0.5 +  # Priority is most important
                (scores['total_demand'] / 100) * 0.3 +  # Normalize demand
                scores['request_count'] * 0.2  # Request frequency
            )
            
            if composite_score > highest_score:
                highest_score = composite_score
                most_aggressive = agent_id
        
        return most_aggressive


class TestInterventionThresholdAccuracy:
    """Property-based tests for intervention threshold accuracy."""
    
    @given(
        risk_score=st.floats(min_value=0.71, max_value=1.0),
        confidence=st.floats(min_value=0.1, max_value=1.0),
        num_agents=st.integers(min_value=1, max_value=5),
        agent_priorities=st.lists(
            st.integers(min_value=1, max_value=10), 
            min_size=1, 
            max_size=5
        ),
        resource_amounts=st.lists(
            st.integers(min_value=1, max_value=100), 
            min_size=1, 
            max_size=5
        )
    )
    @settings(max_examples=100)
    def test_high_risk_triggers_intervention(
        self, 
        risk_score: float, 
        confidence: float, 
        num_agents: int,
        agent_priorities: List[int],
        resource_amounts: List[int]
    ):
        """
        Property: For any conflict analysis with risk score above 0.7, 
        the system should classify it as high-risk requiring intervention.
        
        **Feature: agent-conflict-predictor, Property 5: Intervention threshold accuracy**
        **Validates: Requirements 2.5, 4.1**
        """
        # Ensure we have matching numbers of priorities and amounts
        assume(len(agent_priorities) >= num_agents)
        assume(len(resource_amounts) >= num_agents)
        
        # Create agent intentions for testing aggressive agent identification
        intentions = []
        for i in range(num_agents):
            intention = AgentIntention(
                agent_id=f"agent_{i}",
                resource_type="cpu",
                requested_amount=resource_amounts[i],
                priority_level=agent_priorities[i],
                timestamp=datetime.now()
            )
            intentions.append(intention)
        
        # Create conflict analysis with high risk score
        conflict_analysis = ConflictAnalysis(
            risk_score=risk_score,
            confidence_level=confidence,
            affected_agents=[f"agent_{i}" for i in range(num_agents)],
            predicted_failure_mode="High contention scenario",
            nash_equilibrium=None,
            timestamp=datetime.now()
        )
        
        # Test intervention decision
        should_intervene = InterventionLogic.should_intervene(conflict_analysis)
        risk_classification = InterventionLogic.classify_risk_level(risk_score)
        most_aggressive = InterventionLogic.identify_most_aggressive_agent(intentions)
        
        # Assertions for Property 5
        assert should_intervene is True, f"Risk score {risk_score} > 0.7 should trigger intervention"
        assert risk_classification == "high-risk", f"Risk score {risk_score} should be classified as high-risk"
        assert most_aggressive in [f"agent_{i}" for i in range(num_agents)], "Most aggressive agent should be one of the input agents"
        assert isinstance(most_aggressive, str), "Most aggressive agent should be a string agent ID"
    
    @given(
        risk_score=st.floats(min_value=0.0, max_value=0.7),
        confidence=st.floats(min_value=0.1, max_value=1.0)
    )
    @settings(max_examples=100)
    def test_low_risk_no_intervention(self, risk_score: float, confidence: float):
        """
        Property: For any conflict analysis with risk score at or below 0.7, 
        the system should not classify it as requiring intervention.
        
        **Feature: agent-conflict-predictor, Property 5: Intervention threshold accuracy**
        **Validates: Requirements 2.5, 4.1**
        """
        # Create conflict analysis with low/medium risk score
        conflict_analysis = ConflictAnalysis(
            risk_score=risk_score,
            confidence_level=confidence,
            affected_agents=["agent_1", "agent_2"],
            predicted_failure_mode="Low contention scenario",
            nash_equilibrium=None,
            timestamp=datetime.now()
        )
        
        # Test intervention decision
        should_intervene = InterventionLogic.should_intervene(conflict_analysis)
        risk_classification = InterventionLogic.classify_risk_level(risk_score)
        
        # Assertions for Property 5
        assert should_intervene is False, f"Risk score {risk_score} <= 0.7 should not trigger intervention"
        assert risk_classification in ["low-risk", "medium-risk"], f"Risk score {risk_score} should not be high-risk"
    
    @given(
        intentions_data=st.lists(
            st.tuples(
                st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),  # agent_id
                st.integers(min_value=1, max_value=100),  # requested_amount
                st.integers(min_value=1, max_value=10)    # priority_level
            ),
            min_size=2,
            max_size=10,
            unique_by=lambda x: x[0]  # Unique agent IDs
        )
    )
    @settings(max_examples=100)
    def test_most_aggressive_agent_identification(self, intentions_data):
        """
        Property: For any set of agent intentions, the system should correctly 
        identify the most aggressive agent based on priority, demand, and frequency.
        
        **Feature: agent-conflict-predictor, Property 5: Intervention threshold accuracy**
        **Validates: Requirements 2.5, 4.1**
        """
        # Create agent intentions from generated data
        intentions = []
        for agent_id, amount, priority in intentions_data:
            intention = AgentIntention(
                agent_id=agent_id,
                resource_type="cpu",
                requested_amount=amount,
                priority_level=priority,
                timestamp=datetime.now()
            )
            intentions.append(intention)
        
        # Identify most aggressive agent
        most_aggressive = InterventionLogic.identify_most_aggressive_agent(intentions)
        
        # Verify the result
        assert most_aggressive is not None, "Should identify an aggressive agent"
        assert isinstance(most_aggressive, str), "Agent ID should be a string"
        assert most_aggressive in [intention.agent_id for intention in intentions], "Should be one of the input agents"
        
        # Verify it's actually the most aggressive by checking it has reasonable characteristics
        aggressive_intention = next(i for i in intentions if i.agent_id == most_aggressive)
        
        # Calculate the composite score for the identified agent
        max_priority = max(i.priority_level for i in intentions)
        max_demand = max(i.requested_amount for i in intentions)
        
        # If all agents are identical, any choice is valid
        all_identical = all(
            i.priority_level == intentions[0].priority_level and 
            i.requested_amount == intentions[0].requested_amount 
            for i in intentions
        )
        
        if not all_identical:
            # The most aggressive should not be the least aggressive in all dimensions
            min_priority = min(i.priority_level for i in intentions)
            min_demand = min(i.requested_amount for i in intentions)
            
            assert not (
                aggressive_intention.priority_level == min_priority and
                aggressive_intention.requested_amount == min_demand and
                min_priority < max_priority and  # Only check if there's actually variation
                min_demand < max_demand
            ), "Most aggressive agent should not be least aggressive when there's variation"
    
    @patch('src.prediction_engine.gemini_client.genai')
    def test_integration_with_gemini_client(self, mock_genai):
        """
        Integration test: Verify intervention logic works with actual Gemini client responses.
        
        **Feature: agent-conflict-predictor, Property 5: Intervention threshold accuracy**
        **Validates: Requirements 2.5, 4.1**
        """
        # Mock high-risk Gemini API response
        mock_response = Mock()
        mock_response.text = """
        RISK_SCORE: 0.85
        CONFIDENCE: 0.9
        AFFECTED_AGENTS: agent_1, agent_2, agent_3
        FAILURE_MODE: Critical resource deadlock with cascading failure risk
        NASH_EQUILIBRIUM: Unstable competitive equilibrium
        REASONING: Multiple high-priority agents competing for limited CPU resources
        """
        
        # Mock both the newer and older API structures
        mock_client = Mock()
        mock_client.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client
        
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        # Create test intentions with high contention
        intentions = [
            AgentIntention(
                agent_id="agent_1",
                resource_type="cpu",
                requested_amount=80,
                priority_level=9,
                timestamp=datetime.now()
            ),
            AgentIntention(
                agent_id="agent_2",
                resource_type="cpu",
                requested_amount=70,
                priority_level=8,
                timestamp=datetime.now()
            ),
            AgentIntention(
                agent_id="agent_3",
                resource_type="cpu",
                requested_amount=60,
                priority_level=7,
                timestamp=datetime.now()
            )
        ]
        
        # Execute full workflow
        client = GeminiClient()
        conflict_analysis = client.analyze_conflict_risk(intentions)
        
        # Test intervention logic with real analysis
        should_intervene = InterventionLogic.should_intervene(conflict_analysis)
        risk_classification = InterventionLogic.classify_risk_level(conflict_analysis.risk_score)
        most_aggressive = InterventionLogic.identify_most_aggressive_agent(intentions)
        
        # Verify intervention threshold accuracy
        assert should_intervene is True, "High-risk analysis should trigger intervention"
        assert risk_classification == "high-risk", "Should classify as high-risk"
        assert most_aggressive == "agent_1", "Agent with highest priority and demand should be most aggressive"
        assert conflict_analysis.risk_score > 0.7, "Risk score should exceed threshold"
    
    def test_edge_case_empty_intentions(self):
        """
        Test edge case: Empty intentions list should raise appropriate error.
        
        **Feature: agent-conflict-predictor, Property 5: Intervention threshold accuracy**
        **Validates: Requirements 2.5, 4.1**
        """
        with pytest.raises(ValueError, match="empty intentions"):
            InterventionLogic.identify_most_aggressive_agent([])
    
    def test_edge_case_single_agent(self):
        """
        Test edge case: Single agent should be identified as most aggressive.
        
        **Feature: agent-conflict-predictor, Property 5: Intervention threshold accuracy**
        **Validates: Requirements 2.5, 4.1**
        """
        intention = AgentIntention(
            agent_id="solo_agent",
            resource_type="memory",
            requested_amount=50,
            priority_level=5,
            timestamp=datetime.now()
        )
        
        most_aggressive = InterventionLogic.identify_most_aggressive_agent([intention])
        assert most_aggressive == "solo_agent"
    
    @given(
        risk_score=st.floats(min_value=0.0, max_value=1.0)
    )
    @settings(max_examples=100)
    def test_threshold_boundary_behavior(self, risk_score: float):
        """
        Property: The intervention threshold should have consistent boundary behavior.
        
        **Feature: agent-conflict-predictor, Property 5: Intervention threshold accuracy**
        **Validates: Requirements 2.5, 4.1**
        """
        conflict_analysis = ConflictAnalysis(
            risk_score=risk_score,
            confidence_level=0.8,
            affected_agents=["agent_1"],
            predicted_failure_mode="Test scenario",
            nash_equilibrium=None,
            timestamp=datetime.now()
        )
        
        should_intervene = InterventionLogic.should_intervene(conflict_analysis)
        
        # Verify threshold behavior is consistent
        if risk_score > 0.7:
            assert should_intervene is True, f"Risk score {risk_score} > 0.7 should trigger intervention"
        else:
            assert should_intervene is False, f"Risk score {risk_score} <= 0.7 should not trigger intervention"