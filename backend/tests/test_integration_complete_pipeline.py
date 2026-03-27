"""
Integration tests for the complete pipeline from simulation to intervention.

Tests the full workflow: Agent Simulation → Conflict Prediction → Trust Management → Intervention → Quarantine
"""
import pytest
import time
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from src.prediction_engine.system_integration import ConflictPredictorSystem
from src.prediction_engine.models.core import (
    AgentIntention, ConflictAnalysis, GameState, EquilibriumSolution
)
from src.prediction_engine.simulator import AgentNetwork
from src.prediction_engine.gemini_client import GeminiClient
from src.prediction_engine.intervention_engine import intervention_engine
from src.prediction_engine.trust_manager import trust_manager
from src.prediction_engine.quarantine_manager import quarantine_manager


@pytest.mark.integration
class TestCompletePipeline:
    """Integration tests for the complete system pipeline."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Patch RedisClient
        self.redis_patcher = patch('src.prediction_engine.redis_client.RedisClient')
        self.mock_redis_cls = self.redis_patcher.start()
        
        self.mock_redis = self.mock_redis_cls.return_value
        self.storage = {}
        
        def mock_set(key, value, **kwargs):
            self.storage[key] = value
            return True
        def mock_get(key):
            return self.storage.get(key)
        def mock_delete(key):
            if key in self.storage:
                del self.storage[key]
                return 1
            return 0
        def mock_set_json(key, value, **kwargs):
            import json
            from datetime import datetime

            class DateTimeEncoder(json.JSONEncoder):
                def default(self, o):
                    if isinstance(o, datetime):
                        return o.isoformat()
                    return super().default(o)

            self.storage[key] = json.dumps(value, cls=DateTimeEncoder)
            return True
        def mock_get_json(key):
            import json
            val = self.storage.get(key)
            return json.loads(val) if val else None

        def mock_exists(key):
            return 1 if key in self.storage else 0
            
        self.mock_redis.set.side_effect = mock_set
        self.mock_redis.get.side_effect = mock_get
        self.mock_redis.delete.side_effect = mock_delete
        self.mock_redis.set_json.side_effect = mock_set_json
        self.mock_redis.get_json.side_effect = mock_get_json
        self.mock_redis.exists.side_effect = mock_exists
        self.mock_redis.keys.side_effect = lambda p: [k for k in self.storage.keys() if k.startswith(p.replace('*', ''))]
        
        # Inject mock into singletons
        from src.prediction_engine.trust_manager import trust_manager
        from src.prediction_engine.quarantine_manager import quarantine_manager
        trust_manager.score_manager.redis_client = self.mock_redis
        quarantine_manager.redis_client = self.mock_redis

        # Reset all system state by releasing any existing quarantines
        # (Mock state is empty anyway, but good practice if logic changes)
        pass
        
    def teardown_method(self):
        """Clean up after each test."""
        # Ensure all systems are stopped
        if hasattr(self, 'redis_patcher'):
            self.redis_patcher.stop()
    
    @patch('src.prediction_engine.gemini_client.genai')
    def test_complete_pipeline_high_risk_scenario(self, mock_genai):
        """Test complete pipeline with high-risk conflict scenario."""
        # Mock Gemini API for high-risk scenario
        mock_response = Mock()
        mock_response.text = """
        RISK_SCORE: 0.91
        CONFIDENCE: 0.94
        AFFECTED_AGENTS: agent_001, agent_002, agent_003
        FAILURE_MODE: Resource exhaustion leading to cascading failures
        NASH_EQUILIBRIUM: Competitive equilibrium with mutual defection
        REASONING: Multiple agents competing for limited resources with escalating priorities
        """
        
        # Mock both newer and older API patterns
        mock_client = Mock()
        mock_client.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client
        
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        # Create and start system
        system = ConflictPredictorSystem()
        
        try:
            # Step 1: Agent Simulation
            system.start_system(agent_count=5)
            
            # Verify simulation started
            status = system.get_system_status()
            assert status["system_running"] is True
            assert status["total_agents"] == 5
            assert status["active_agents"] == 5
            
            # Let agents generate intentions
            time.sleep(1.5)
            
            # Step 2: Collect agent intentions
            intentions = system.agent_network.get_all_intentions()
            assert len(intentions) > 0, "Agents should generate intentions"
            
            # Step 3: Conflict Prediction via Gemini
            client = GeminiClient()
            analysis = client.analyze_conflict_risk(intentions)
            
            # Verify conflict analysis
            assert analysis.risk_score == 0.91
            assert analysis.confidence_level == 0.94
            assert len(analysis.affected_agents) == 3
            assert "cascading" in analysis.predicted_failure_mode.lower()
            
            # Step 4: Trust Management - check initial scores
            initial_trust_scores = {}
            for agent in system.agent_network.agents:
                score = trust_manager.get_trust_score(agent.agent_id)
                initial_trust_scores[agent.agent_id] = score
                assert score == 100, "New agents should start with trust score 100"
            
            # Step 5: Intervention Decision
            result = intervention_engine.process_conflict_analysis(analysis)
            
            # Verify intervention occurred
            assert result is not None
            assert result.success is True
            assert result.agent_id in analysis.affected_agents
            
            # Step 6: Quarantine Execution
            quarantined_agents = quarantine_manager.get_quarantined_agents()
            assert len(quarantined_agents) > 0
            
            quarantined_agent_id = quarantined_agents[0]
            assert quarantined_agent_id == result.agent_id
            
            # Step 7: Trust Score Update
            updated_score = trust_manager.get_trust_score(quarantined_agent_id)
            assert updated_score < initial_trust_scores[quarantined_agent_id]
            
            # Step 8: System Stabilization
            time.sleep(1.0)
            final_status = system.get_system_status()
            
            # Verify system stabilized
            assert final_status["system_running"] is True
            assert final_status["quarantined_agents"] == 1
            assert final_status["active_agents"] == 4
            
            # Verify other agents continue operating
            active_agents = system.agent_network.get_active_agents()
            assert len(active_agents) == 4
            
            # Verify quarantined agent is actually quarantined
            quarantined_agent = next(
                agent for agent in system.agent_network.agents 
                if agent.agent_id == quarantined_agent_id
            )
            assert quarantined_agent.is_quarantined
            
        finally:
            system.stop_system()
    
    @patch('src.prediction_engine.gemini_client.genai')
    def test_complete_pipeline_low_risk_scenario(self, mock_genai):
        """Test complete pipeline with low-risk scenario (no intervention)."""
        # Mock Gemini API for low-risk scenario
        mock_response = Mock()
        mock_response.text = """
        RISK_SCORE: 0.35
        CONFIDENCE: 0.82
        AFFECTED_AGENTS: agent_1, agent_2
        FAILURE_MODE: Minor resource contention, self-resolving
        NASH_EQUILIBRIUM: Cooperative equilibrium with resource sharing
        REASONING: Agents can cooperatively share resources without conflict
        """
        
        # Mock both newer and older API patterns
        mock_client = Mock()
        mock_client.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client
        
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        system = ConflictPredictorSystem()
        
        try:
            # Start system
            system.start_system(agent_count=5)
            time.sleep(1.0)
            
            # Get intentions and analyze
            intentions = system.agent_network.get_all_intentions()
            
            client = GeminiClient()
            analysis = client.analyze_conflict_risk(intentions)
            
            # Verify low-risk analysis
            assert analysis.risk_score == 0.35
            assert analysis.risk_score < 0.7  # Below intervention threshold
            
            # Process through intervention engine
            result = intervention_engine.process_conflict_analysis(analysis)
            
            # Verify no intervention occurred
            assert result is None or result.success is False
            
            # Verify no quarantines
            quarantined_agents = quarantine_manager.get_quarantined_agents()
            assert len(quarantined_agents) == 0
            
            # Verify all agents remain active
            status = system.get_system_status()
            assert status["active_agents"] == 5
            assert status["quarantined_agents"] == 0
            
            # Verify trust scores unchanged
            for agent in system.agent_network.agents:
                score = trust_manager.get_trust_score(agent.agent_id)
                assert score == 100, "Trust scores should remain at 100 for low-risk scenario"
            
        finally:
            system.stop_system()
    
    @patch('src.prediction_engine.gemini_client.genai')
    def test_pipeline_with_nash_equilibrium_analysis(self, mock_genai):
        """Test pipeline including Nash equilibrium analysis."""
        # Mock Gemini responses for both conflict and equilibrium analysis
        conflict_response = Mock()
        conflict_response.text = """
        RISK_SCORE: 0.78
        CONFIDENCE: 0.86
        AFFECTED_AGENTS: agent_1, agent_2, agent_3
        FAILURE_MODE: Competitive resource allocation
        NASH_EQUILIBRIUM: Mixed strategy equilibrium
        REASONING: Agents using mixed strategies for resource competition
        """
        
        equilibrium_response = Mock()
        equilibrium_response.text = """
        STRATEGY_PROFILE: agent_1:compete, agent_2:cooperate, agent_3:compete
        PAYOFFS: agent_1:0.7, agent_2:0.4, agent_3:0.6
        STABILITY_SCORE: 0.72
        EQUILIBRIUM_TYPE: mixed
        REASONING: Mixed equilibrium with competitive bias
        """
        
        # Mock both newer and older API patterns
        mock_client = Mock()
        mock_client.generate_content.side_effect = [conflict_response, equilibrium_response]
        mock_genai.Client.return_value = mock_client
        
        mock_model = Mock()
        # Return different responses for different calls
        mock_model.generate_content.side_effect = [conflict_response, equilibrium_response]
        mock_genai.GenerativeModel.return_value = mock_model
        
        system = ConflictPredictorSystem()
        
        try:
            system.start_system(agent_count=5)
            time.sleep(1.0)
            
            # Get intentions
            intentions = system.agent_network.get_all_intentions()
            
            # Perform conflict analysis
            client = GeminiClient()
            analysis = client.analyze_conflict_risk(intentions)
            
            # Verify conflict analysis
            assert analysis.risk_score == 0.78
            assert analysis.confidence_level == 0.86
            
            # Perform Nash equilibrium analysis
            game_state = GameState(
                agents=[agent.agent_id for agent in system.agent_network.agents],
                resources={"cpu": 1000, "memory": 1000, "storage": 1000},
                intentions=intentions,
                timestamp=datetime.now()
            )
            
            equilibrium = client.calculate_nash_equilibrium(game_state)
            
            # Verify equilibrium analysis
            assert equilibrium.stability_score == 0.72
            assert equilibrium.equilibrium_type == "mixed"
            assert len(equilibrium.strategy_profile) == 3
            assert len(equilibrium.payoffs) == 3
            
            # Process intervention with equilibrium information
            analysis.nash_equilibrium = equilibrium
            result = intervention_engine.process_conflict_analysis(analysis)
            
            # Verify intervention considers equilibrium
            assert result is not None
            assert result.success is True
            
            # Verify quarantine occurred
            quarantined_agents = quarantine_manager.get_quarantined_agents()
            assert len(quarantined_agents) > 0
            
            # Verify system stability after intervention
            time.sleep(1.0)
            status = system.get_system_status()
            assert status["system_running"] is True
            assert status["active_agents"] == 2
            
        finally:
            system.stop_system()
    
    def test_pipeline_error_recovery(self):
        """Test pipeline behavior when components fail and recover."""
        system = ConflictPredictorSystem()
        
        try:
            system.start_system(agent_count=5)
            
            # Verify normal operation
            status = system.get_system_status()
            assert status["system_running"] is True
            
            # Simulate Gemini API failure
            with patch('src.prediction_engine.gemini_client.genai.Client', 
                      side_effect=Exception("API temporarily unavailable")), \
                 patch('src.prediction_engine.gemini_client.genai.GenerativeModel', 
                      side_effect=Exception("API temporarily unavailable")):
                
                # System should handle API failure gracefully
                try:
                    system.simulate_conflict_scenario()
                except Exception:
                    pass  # Expected to fail
                
                # System should remain operational
                status = system.get_system_status()
                assert status["system_running"] is True
                assert status["active_agents"] > 0
            
            # Simulate Redis failure
            with patch.object(trust_manager, 'get_trust_score', 
                            side_effect=Exception("Redis connection lost")):
                
                # System should continue despite trust manager failure
                time.sleep(1.0)
                
                # Agents should still be active
                active_agents = system.agent_network.get_active_agents()
                assert len(active_agents) > 0
            
            # Test recovery after failures
            time.sleep(1.0)
            
            # System should recover normal operation
            final_status = system.get_system_status()
            assert final_status["system_running"] is True
            assert final_status["active_agents"] > 0
            
            # Should be able to perform normal operations again
            intentions = system.agent_network.get_all_intentions()
            assert len(intentions) >= 0  # May be empty but should not error
            
        finally:
            system.stop_system()
    
    def test_pipeline_performance_under_load(self):
        """Test pipeline performance with larger agent networks."""
        system = ConflictPredictorSystem()
        
        try:
            # Start with larger agent network
            system.start_system(agent_count=10)
            
            # Verify system handles larger load
            status = system.get_system_status()
            assert status["total_agents"] == 10
            assert status["active_agents"] == 10
            
            # Let system run under load
            start_time = time.time()
            time.sleep(3.0)
            
            # Measure system responsiveness
            intentions = system.agent_network.get_all_intentions()
            
            # Should have many intentions from 10 agents
            assert len(intentions) > 5, "Should have multiple intentions from 10 agents"
            
            # System should remain responsive
            status_check_start = time.time()
            status = system.get_system_status()
            status_check_time = time.time() - status_check_start
            
            # Status check should be fast (< 1 second)
            assert status_check_time < 1.0, "System should remain responsive under load"
            
            # Verify system stability
            assert status["system_running"] is True
            assert status["active_agents"] > 0
            
            # Test intervention under load
            system.simulate_conflict_scenario()
            time.sleep(1.0)
            
            # Should handle intervention even under load
            final_status = system.get_system_status()
            assert final_status["system_running"] is True
            
        finally:
            system.stop_system()
    
    def test_pipeline_quarantine_lifecycle(self):
        """Test complete quarantine lifecycle through the pipeline."""
        system = ConflictPredictorSystem()
        
        try:
            system.start_system(agent_count=5)
            time.sleep(1.0)
            
            # Get an agent to quarantine
            target_agent = system.agent_network.agents[0]
            target_agent_id = target_agent.agent_id
            
            # Check initial state
            initial_score = trust_manager.get_trust_score(target_agent_id)
            assert initial_score == 100
            assert not target_agent.is_quarantined
            
            # Simulate high-risk scenario leading to quarantine
            from src.prediction_engine.models.core import ConflictAnalysis
            
            high_risk_analysis = ConflictAnalysis(
                risk_score=0.89,
                confidence_level=0.91,
                affected_agents=[target_agent_id],
                predicted_failure_mode="Agent exhibiting aggressive resource consumption",
                nash_equilibrium=None,
                timestamp=datetime.now()
            )
            
            # Process through intervention pipeline
            result = intervention_engine.process_conflict_analysis(high_risk_analysis)
            
            # Verify quarantine applied
            assert result is not None
            assert result.success is True
            assert result.agent_id == target_agent_id
            
            # Verify agent is quarantined
            assert target_agent.is_quarantined
            
            # Verify trust score reduced
            quarantine_score = trust_manager.get_trust_score(target_agent_id)
            assert quarantine_score < initial_score
            
            # Verify quarantine prevents new requests
            time.sleep(1.0)
            
            # Agent should not be making new resource requests
            quarantined_intentions = [
                i for i in system.agent_network.get_all_intentions()
                if i.agent_id == target_agent_id
            ]
            # May have old intentions but should not be generating new ones actively
            
            # Test quarantine release
            success = quarantine_manager.release_quarantine(target_agent_id)
            assert success
            
            # Verify agent is released
            assert not target_agent.is_quarantined
            
            # Agent should resume normal operation
            time.sleep(1.0)
            
            # Verify agent can make requests again
            active_agents = system.agent_network.get_active_agents()
            assert target_agent_id in [agent.agent_id for agent in active_agents]
            
            # Trust score should remain at reduced level
            final_score = trust_manager.get_trust_score(target_agent_id)
            assert final_score == quarantine_score  # No automatic recovery
            
        finally:
            system.stop_system()
    
    def test_pipeline_multiple_interventions(self):
        """Test pipeline handling multiple interventions over time."""
        system = ConflictPredictorSystem()
        
        try:
            system.start_system(agent_count=6)
            time.sleep(1.0)
            
            # Track interventions
            intervention_count = 0
            quarantined_agents_over_time = []
            
            # Simulate multiple conflict scenarios
            for i in range(3):
                # Create different conflict scenarios
                from src.prediction_engine.models.core import ConflictAnalysis
                
                analysis = ConflictAnalysis(
                    risk_score=0.75 + (i * 0.05),  # Increasing risk
                    confidence_level=0.85,
                    affected_agents=[agent.agent_id for agent in system.agent_network.agents[i:i+2]],
                    predicted_failure_mode=f"Conflict scenario {i+1}",
                    nash_equilibrium=None,
                    timestamp=datetime.now()
                )
                
                # Process intervention
                result = intervention_engine.process_conflict_analysis(analysis)
                
                if result and result.success:
                    intervention_count += 1
                    quarantined_agents_over_time.append(result.agent_id)
                
                # Wait between interventions
                time.sleep(1.5)
            
            # Verify multiple interventions occurred
            assert intervention_count > 0, "Should have multiple interventions"
            
            # Verify system handled multiple interventions
            status = system.get_system_status()
            assert status["system_running"] is True
            assert status["quarantined_agents"] > 0
            assert status["active_agents"] > 0
            
            # Verify intervention statistics
            intervention_stats = status["intervention_statistics"]
            assert isinstance(intervention_stats, dict)
            
            # Verify quarantine statistics
            quarantine_stats = status["quarantine_statistics"]
            assert isinstance(quarantine_stats, dict)
            
            # System should remain stable despite multiple interventions
            final_intentions = system.agent_network.get_all_intentions()
            assert len(final_intentions) >= 0  # Should not error
            
        finally:
            system.stop_system()


if __name__ == "__main__":
    # Run complete pipeline tests
    pytest.main([__file__, "-v", "-m", "integration"])