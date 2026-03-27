"""
Tests for the intervention engine implementation.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.prediction_engine.intervention_engine import ConflictInterventionEngine
from src.prediction_engine.models.core import ConflictAnalysis, QuarantineResult
from src.prediction_engine.interfaces import TrustManager, QuarantineManager


class TestConflictInterventionEngine:
    """Test cases for the ConflictInterventionEngine class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_trust_manager = Mock(spec=TrustManager)
        self.mock_quarantine_manager = Mock(spec=QuarantineManager)
        
        self.engine = ConflictInterventionEngine(
            trust_manager_instance=self.mock_trust_manager,
            quarantine_manager_instance=self.mock_quarantine_manager
        )
    
    def test_initialization(self):
        """Test intervention engine initialization."""
        assert self.engine.trust_manager == self.mock_trust_manager
        assert self.engine.quarantine_manager == self.mock_quarantine_manager
        assert self.engine.conflict_risk_threshold == 0.7  # Default from config
        assert self.engine.intervention_history == []
    
    def test_evaluate_intervention_need_high_risk(self):
        """Test intervention evaluation for high-risk scenarios."""
        conflict_analysis = ConflictAnalysis(
            risk_score=0.85,
            confidence_level=0.9,
            affected_agents=["agent_001", "agent_002"],
            predicted_failure_mode="Resource contention",
            nash_equilibrium=None,
            timestamp=datetime.now()
        )
        
        result = self.engine.evaluate_intervention_need(conflict_analysis)
        assert result is True
    
    def test_evaluate_intervention_need_low_risk(self):
        """Test intervention evaluation for low-risk scenarios."""
        conflict_analysis = ConflictAnalysis(
            risk_score=0.5,
            confidence_level=0.8,
            affected_agents=["agent_001", "agent_002"],
            predicted_failure_mode="Minor resource contention",
            nash_equilibrium=None,
            timestamp=datetime.now()
        )
        
        result = self.engine.evaluate_intervention_need(conflict_analysis)
        assert result is False
    
    def test_evaluate_intervention_need_threshold_boundary(self):
        """Test intervention evaluation at threshold boundary."""
        # Exactly at threshold should not trigger intervention
        conflict_analysis = ConflictAnalysis(
            risk_score=0.7,
            confidence_level=0.8,
            affected_agents=["agent_001"],
            predicted_failure_mode="Threshold test",
            nash_equilibrium=None,
            timestamp=datetime.now()
        )
        
        result = self.engine.evaluate_intervention_need(conflict_analysis)
        assert result is False
        
        # Just above threshold should trigger intervention
        conflict_analysis.risk_score = 0.71
        result = self.engine.evaluate_intervention_need(conflict_analysis)
        assert result is True
    
    def test_identify_most_aggressive_agent(self):
        """Test identification of most aggressive agent."""
        agents = ["agent_001", "agent_002", "agent_003"]
        
        # Mock trust scores (lower = more aggressive)
        self.mock_trust_manager.get_trust_score.side_effect = lambda agent_id: {
            "agent_001": 80,  # High trust
            "agent_002": 25,  # Low trust (most aggressive)
            "agent_003": 60   # Medium trust
        }[agent_id]
        
        # Mock quarantine counts
        self.mock_trust_manager.get_quarantine_count = Mock(return_value=0)
        
        result = self.engine.identify_most_aggressive_agent(agents)
        assert result == "agent_002"
    
    def test_identify_most_aggressive_agent_empty_list(self):
        """Test identification with empty agent list."""
        with pytest.raises(ValueError, match="No agents provided"):
            self.engine.identify_most_aggressive_agent([])
    
    def test_execute_quarantine_success(self):
        """Test successful quarantine execution."""
        agent_id = "agent_001"
        reason = "High conflict risk"
        
        # Mock successful quarantine
        mock_result = QuarantineResult(
            success=True,
            agent_id=agent_id,
            reason=f"Successfully quarantined: {reason}",
            timestamp=datetime.now()
        )
        self.mock_quarantine_manager.quarantine_agent.return_value = mock_result
        
        result = self.engine.execute_quarantine(agent_id, reason)
        
        assert result.success is True
        assert result.agent_id == agent_id
        
        # Verify trust score was updated
        self.mock_trust_manager.update_trust_score.assert_called_once_with(
            agent_id, -20, f"Quarantined: {reason}"
        )
        
        # Verify intervention was recorded
        assert len(self.engine.intervention_history) == 1
        intervention = self.engine.intervention_history[0]
        assert intervention.action_type == "quarantine"
        assert intervention.target_agent == agent_id
        assert intervention.reason == reason
    
    def test_execute_quarantine_failure(self):
        """Test quarantine execution failure."""
        agent_id = "agent_001"
        reason = "High conflict risk"
        
        # Mock failed quarantine
        mock_result = QuarantineResult(
            success=False,
            agent_id=agent_id,
            reason="Quarantine failed: Agent not found",
            timestamp=datetime.now()
        )
        self.mock_quarantine_manager.quarantine_agent.return_value = mock_result
        
        result = self.engine.execute_quarantine(agent_id, reason)
        
        assert result.success is False
        assert result.agent_id == agent_id
        
        # Trust score should not be updated on failure
        self.mock_trust_manager.update_trust_score.assert_not_called()
        
        # Intervention should not be recorded on failure
        assert len(self.engine.intervention_history) == 0
    
    @patch('src.prediction_engine.intervention_engine.quarantine_manager', None)
    def test_execute_quarantine_no_manager(self):
        """Test quarantine execution without quarantine manager."""
        # Create engine with no quarantine manager and mock trust manager
        mock_trust_manager = Mock(spec=TrustManager)
        engine = ConflictInterventionEngine(
            trust_manager_instance=mock_trust_manager,
            quarantine_manager_instance=None
        )
        
        result = engine.execute_quarantine("agent_001", "Test reason")
        
        assert result.success is False
        assert "No quarantine manager available" in result.reason
    
    def test_process_conflict_analysis_intervention_needed(self):
        """Test processing conflict analysis that requires intervention."""
        conflict_analysis = ConflictAnalysis(
            risk_score=0.85,
            confidence_level=0.9,
            affected_agents=["agent_001", "agent_002"],
            predicted_failure_mode="Resource contention",
            nash_equilibrium=None,
            timestamp=datetime.now()
        )
        
        # Mock trust scores
        self.mock_trust_manager.get_trust_score.side_effect = lambda agent_id: {
            "agent_001": 25,  # Low trust (most aggressive)
            "agent_002": 60   # Medium trust
        }[agent_id]
        
        self.mock_trust_manager.get_quarantine_count = Mock(return_value=0)
        
        # Mock successful quarantine
        mock_result = QuarantineResult(
            success=True,
            agent_id="agent_001",
            reason="Successfully quarantined",
            timestamp=datetime.now()
        )
        self.mock_quarantine_manager.quarantine_agent.return_value = mock_result
        
        result = self.engine.process_conflict_analysis(conflict_analysis)
        
        assert result is not None
        assert result.success is True
        assert result.agent_id == "agent_001"
    
    def test_process_conflict_analysis_no_intervention_needed(self):
        """Test processing conflict analysis that doesn't require intervention."""
        conflict_analysis = ConflictAnalysis(
            risk_score=0.5,  # Below threshold
            confidence_level=0.8,
            affected_agents=["agent_001", "agent_002"],
            predicted_failure_mode="Minor contention",
            nash_equilibrium=None,
            timestamp=datetime.now()
        )
        
        result = self.engine.process_conflict_analysis(conflict_analysis)
        
        assert result is None
        self.mock_quarantine_manager.quarantine_agent.assert_not_called()
    
    def test_process_conflict_analysis_no_affected_agents(self):
        """Test processing conflict analysis with no affected agents."""
        conflict_analysis = ConflictAnalysis(
            risk_score=0.85,
            confidence_level=0.9,
            affected_agents=[],  # No affected agents
            predicted_failure_mode="Resource contention",
            nash_equilibrium=None,
            timestamp=datetime.now()
        )
        
        result = self.engine.process_conflict_analysis(conflict_analysis)
        
        assert result is None
        self.mock_quarantine_manager.quarantine_agent.assert_not_called()
    
    def test_get_intervention_history(self):
        """Test getting intervention history."""
        # Add some mock interventions
        from src.prediction_engine.models.core import InterventionAction
        
        intervention1 = InterventionAction(
            action_type="quarantine",
            target_agent="agent_001",
            reason="High risk",
            confidence=1.0,
            timestamp=datetime.now()
        )
        
        intervention2 = InterventionAction(
            action_type="quarantine",
            target_agent="agent_002",
            reason="Aggressive behavior",
            confidence=0.9,
            timestamp=datetime.now()
        )
        
        self.engine.intervention_history = [intervention1, intervention2]
        
        history = self.engine.get_intervention_history()
        
        assert len(history) == 2
        assert history[0] == intervention1
        assert history[1] == intervention2
        
        # Verify it returns a copy
        history.append("test")
        assert len(self.engine.intervention_history) == 2
    
    def test_get_statistics(self):
        """Test getting intervention statistics."""
        # Add some mock interventions
        from src.prediction_engine.models.core import InterventionAction
        
        interventions = [
            InterventionAction("quarantine", "agent_001", "reason1", 1.0, datetime.now()),
            InterventionAction("quarantine", "agent_002", "reason2", 0.9, datetime.now()),
            InterventionAction("other", "agent_003", "reason3", 0.8, datetime.now())
        ]
        
        self.engine.intervention_history = interventions
        
        stats = self.engine.get_statistics()
        
        assert stats["total_interventions"] == 3
        assert stats["quarantine_actions"] == 2
        assert stats["other_actions"] == 1
    
    def test_intervention_history_limit(self):
        """Test that intervention history is limited to 100 entries."""
        from src.prediction_engine.models.core import InterventionAction
        
        # Add 105 interventions
        for i in range(105):
            intervention = InterventionAction(
                action_type="quarantine",
                target_agent=f"agent_{i:03d}",
                reason=f"reason_{i}",
                confidence=1.0,
                timestamp=datetime.now()
            )
            self.engine.intervention_history.append(intervention)
        
        # Simulate executing a quarantine to trigger history cleanup
        mock_result = QuarantineResult(
            success=True,
            agent_id="agent_new",
            reason="Test",
            timestamp=datetime.now()
        )
        self.mock_quarantine_manager.quarantine_agent.return_value = mock_result
        
        self.engine.execute_quarantine("agent_new", "Test")
        
        # Should be limited to 100 entries
        assert len(self.engine.intervention_history) == 100
        
        # Should keep the most recent entries
        assert self.engine.intervention_history[-1].target_agent == "agent_new"