"""
Integration tests for specific failure scenarios including CDN cache stampede,
cascading failures, and other real-world conflict patterns.
"""
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.prediction_engine.simulator import AgentNetwork
from src.prediction_engine.models.core import (
    AgentIntention, ConflictAnalysis, ResourceType, GameState
)
from src.prediction_engine.intervention_engine import intervention_engine
from src.prediction_engine.quarantine_manager import quarantine_manager
from src.prediction_engine.trust_manager import trust_manager
from src.integrations.kafka_client import KafkaOperationError


@pytest.mark.integration
class TestFailureScenarios:
    """Integration tests for specific failure scenarios."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Reset system state by releasing any existing quarantines
        quarantined_agents = quarantine_manager.get_quarantined_agents()
        for agent_id in quarantined_agents:
            quarantine_manager.release_quarantine(agent_id)
    
    def teardown_method(self):
        """Clean up after each test."""
        # Clean up any running simulations
        pass
    
    def test_cdn_cache_stampede_detection_and_prevention(self):
        """Test detection and prevention of CDN cache stampede scenarios."""
        # Create network with agents that will cause cache stampede
        network = AgentNetwork(agent_count=8)
        
        try:
            # Create agents
            agents = network.create_agents()
            
            # Simulate cache stampede: multiple agents requesting same cached content
            cache_key = "popular_content_cache"
            stampede_time = datetime.now()
            
            # Create simultaneous high-priority requests for same cache key
            stampede_intentions = []
            for i, agent in enumerate(agents):
                intention = AgentIntention(
                    agent_id=agent.agent_id,
                    resource_type=cache_key,
                    requested_amount=50,  # Each wants significant portion
                    priority_level=9,     # High priority
                    timestamp=stampede_time + timedelta(milliseconds=i*5)  # Nearly simultaneous
                )
                stampede_intentions.append(intention)
                
                # Set agent intentions to simulate stampede
                agent._current_intentions = [intention]
            
            # Start simulation
            network.start_simulation()
            time.sleep(1.5)
            
            # Verify stampede scenario is active
            all_intentions = network.get_all_intentions()
            cache_requests = [i for i in all_intentions if cache_key in i.resource_type]
            assert len(cache_requests) >= 6, "Should have multiple cache requests"
            
            # Create conflict analysis for cache stampede
            stampede_analysis = ConflictAnalysis(
                risk_score=0.92,
                confidence_level=0.88,
                affected_agents=[agent.agent_id for agent in agents],
                predicted_failure_mode="CDN cache stampede: simultaneous requests for same content causing cache invalidation and origin server overload",
                nash_equilibrium=None,
                timestamp=datetime.now()
            )
            
            # Process through intervention system
            result = intervention_engine.process_conflict_analysis(stampede_analysis)
            
            # Verify intervention occurred
            assert result is not None
            assert result.success is True
            
            # Verify most aggressive agent was identified and quarantined
            quarantined_agents = quarantine_manager.get_quarantined_agents()
            assert len(quarantined_agents) > 0
            
            # Verify quarantined agent was one of the stampede participants
            quarantined_agent_id = quarantined_agents[0]
            assert quarantined_agent_id in [agent.agent_id for agent in agents]
            
            # Verify other agents can continue (stampede pressure reduced)
            time.sleep(1.0)
            active_agents = network.get_active_agents()
            assert len(active_agents) >= 6, "Most agents should remain active"
            
            # Verify trust score impact
            quarantined_score = trust_manager.get_trust_score(quarantined_agent_id)
            assert quarantined_score < 100, "Quarantined agent should have reduced trust"
            
        finally:
            network.stop_simulation()
    
    def test_cascading_failure_prevention(self):
        """Test prevention of cascading failures across agent network."""
        network = AgentNetwork(agent_count=10)
        
        try:
            # Create larger network for cascading failure testing
            agents = network.create_agents()
            network.start_simulation()
            
            # Simulate initial failure trigger: resource exhaustion
            # Consume most CPU resources to create pressure
            for i in range(3):
                request = network.resource_manager.process_request(
                    type('MockRequest', (), {
                        'agent_id': f'external_load_{i}',
                        'resource_type': 'cpu',
                        'amount': 250,  # Total 750/1000 CPU used
                        'priority': 8,
                        'timestamp': datetime.now()
                    })()
                )
                assert request.success
            
            # Let agents compete for remaining resources
            time.sleep(2.0)
            
            # Simulate detection of cascading failure pattern
            # Multiple agents failing to get resources, increasing their priority
            failing_agents = agents[:5]  # First 5 agents are "failing"
            
            cascading_analysis = ConflictAnalysis(
                risk_score=0.88,
                confidence_level=0.91,
                affected_agents=[agent.agent_id for agent in failing_agents],
                predicted_failure_mode="Cascading failure: resource exhaustion causing agents to increase priority, creating positive feedback loop",
                nash_equilibrium=None,
                timestamp=datetime.now()
            )
            
            # Process intervention
            result = intervention_engine.process_conflict_analysis(cascading_analysis)
            
            # Verify intervention prevented cascade
            assert result is not None
            assert result.success is True
            
            # Verify system stability after intervention
            time.sleep(1.0)
            
            # Should have quarantined the most aggressive agent
            quarantined_agents = quarantine_manager.get_quarantined_agents()
            assert len(quarantined_agents) > 0
            
            # Remaining agents should be stable
            active_agents = network.get_active_agents()
            assert len(active_agents) >= 8, "Most agents should remain active"
            
            # Verify no further cascading by checking resource contention
            contention_events = network.resource_manager.detect_contention()
            # Contention should be manageable (not growing)
            
        finally:
            network.stop_simulation()
    
    def test_deadlock_detection_and_resolution(self):
        """Test detection and resolution of agent deadlock scenarios."""
        network = AgentNetwork(agent_count=4)
        
        try:
            # Create agents for deadlock scenario
            agents = network.create_agents()
            
            # Simulate circular dependency deadlock
            # Agent A wants resource 1, holds resource 2
            # Agent B wants resource 2, holds resource 3  
            # Agent C wants resource 3, holds resource 4
            # Agent D wants resource 4, holds resource 1
            
            deadlock_intentions = [
                AgentIntention(
                    agent_id=agents[0].agent_id,
                    resource_type="resource_1",
                    requested_amount=100,
                    priority_level=8,
                    timestamp=datetime.now()
                ),
                AgentIntention(
                    agent_id=agents[1].agent_id,
                    resource_type="resource_2", 
                    requested_amount=100,
                    priority_level=8,
                    timestamp=datetime.now()
                ),
                AgentIntention(
                    agent_id=agents[2].agent_id,
                    resource_type="resource_3",
                    requested_amount=100,
                    priority_level=8,
                    timestamp=datetime.now()
                ),
                AgentIntention(
                    agent_id=agents[3].agent_id,
                    resource_type="resource_4",
                    requested_amount=100,
                    priority_level=8,
                    timestamp=datetime.now()
                )
            ]
            
            # Set agent intentions
            for i, agent in enumerate(agents):
                agent._current_intentions = [deadlock_intentions[i]]
            
            # Pre-allocate resources to create circular dependency
            for i in range(4):
                next_resource = f"resource_{((i + 1) % 4) + 1}"
                request = network.resource_manager.process_request(
                    type('MockRequest', (), {
                        'agent_id': agents[i].agent_id,
                        'resource_type': next_resource,
                        'amount': 100,
                        'priority': 5,
                        'timestamp': datetime.now()
                    })()
                )
            
            network.start_simulation()
            time.sleep(1.5)
            
            # Create deadlock analysis
            deadlock_analysis = ConflictAnalysis(
                risk_score=0.95,
                confidence_level=0.93,
                affected_agents=[agent.agent_id for agent in agents],
                predicted_failure_mode="Circular resource dependency deadlock: agents waiting for resources held by each other",
                nash_equilibrium=None,
                timestamp=datetime.now()
            )
            
            # Process intervention
            result = intervention_engine.process_conflict_analysis(deadlock_analysis)
            
            # Verify deadlock resolution
            assert result is not None
            assert result.success is True
            
            # Should quarantine one agent to break the cycle
            quarantined_agents = quarantine_manager.get_quarantined_agents()
            assert len(quarantined_agents) > 0
            
            # Verify deadlock is broken - other agents should be able to proceed
            time.sleep(1.0)
            active_agents = network.get_active_agents()
            assert len(active_agents) >= 3, "Remaining agents should be active"
            
        finally:
            network.stop_simulation()
    
    def test_resource_starvation_scenario(self):
        """Test detection and handling of resource starvation scenarios."""
        network = AgentNetwork(agent_count=6)
        
        try:
            agents = network.create_agents()
            
            # Create scenario where high-priority agents starve low-priority ones
            high_priority_agents = agents[:2]
            low_priority_agents = agents[2:]
            
            # High priority agents get most resources
            for agent in high_priority_agents:
                intention = AgentIntention(
                    agent_id=agent.agent_id,
                    resource_type="memory",
                    requested_amount=400,  # Large requests
                    priority_level=9,      # High priority
                    timestamp=datetime.now()
                )
                agent._current_intentions = [intention]
            
            # Low priority agents get starved
            for agent in low_priority_agents:
                intention = AgentIntention(
                    agent_id=agent.agent_id,
                    resource_type="memory",
                    requested_amount=50,   # Small requests
                    priority_level=2,      # Low priority
                    timestamp=datetime.now()
                )
                agent._current_intentions = [intention]
            
            network.start_simulation()
            time.sleep(2.0)
            
            # Simulate starvation detection
            starvation_analysis = ConflictAnalysis(
                risk_score=0.78,
                confidence_level=0.85,
                affected_agents=[agent.agent_id for agent in low_priority_agents],
                predicted_failure_mode="Resource starvation: high-priority agents monopolizing resources, preventing low-priority agents from making progress",
                nash_equilibrium=None,
                timestamp=datetime.now()
            )
            
            # Process intervention
            result = intervention_engine.process_conflict_analysis(starvation_analysis)
            
            # Verify intervention occurred
            assert result is not None
            assert result.success is True
            
            # Should quarantine one of the high-priority agents
            quarantined_agents = quarantine_manager.get_quarantined_agents()
            assert len(quarantined_agents) > 0
            
            quarantined_id = quarantined_agents[0]
            # Quarantined agent should be one of the high-priority ones
            high_priority_ids = [agent.agent_id for agent in high_priority_agents]
            assert quarantined_id in high_priority_ids, "Should quarantine high-priority agent causing starvation"
            
            # Verify system balance improved
            time.sleep(1.0)
            active_agents = network.get_active_agents()
            assert len(active_agents) >= 5, "Most agents should remain active"
            
        finally:
            network.stop_simulation()
    
    @patch('src.prediction_engine.gemini_client.genai')
    def test_thundering_herd_scenario(self, mock_genai):
        """Test thundering herd scenario where many agents wake up simultaneously."""
        # Mock Gemini response for thundering herd
        mock_response = Mock()
        mock_response.text = """
        RISK_SCORE: 0.87
        CONFIDENCE: 0.89
        AFFECTED_AGENTS: agent_1, agent_2, agent_3, agent_4, agent_5, agent_6
        FAILURE_MODE: Thundering herd: simultaneous wake-up causing resource spike
        NASH_EQUILIBRIUM: Competitive equilibrium with resource contention
        REASONING: Multiple agents simultaneously requesting resources after idle period
        """
        
        # Mock both newer and older API patterns
        mock_client = Mock()
        mock_client.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client
        
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        network = AgentNetwork(agent_count=6)
        
        try:
            agents = network.create_agents()
            
            # Simulate thundering herd: all agents wake up at same time
            wake_time = datetime.now()
            
            for i, agent in enumerate(agents):
                # All agents request resources at nearly the same time
                intention = AgentIntention(
                    agent_id=agent.agent_id,
                    resource_type="cpu",
                    requested_amount=200,  # Significant resource request
                    priority_level=7,
                    timestamp=wake_time + timedelta(milliseconds=i*2)  # Very close timing
                )
                agent._current_intentions = [intention]
            
            network.start_simulation()
            time.sleep(1.0)
            
            # Get intentions for Gemini analysis
            intentions = network.get_all_intentions()
            
            # Analyze through Gemini client
            from src.prediction_engine.gemini_client import GeminiClient
            client = GeminiClient()
            analysis = client.analyze_conflict_risk(intentions)
            
            # Verify thundering herd detected
            assert analysis.risk_score == 0.87
            assert "thundering herd" in analysis.predicted_failure_mode.lower()
            assert len(analysis.affected_agents) == 6
            
            # Process intervention
            result = intervention_engine.process_conflict_analysis(analysis)
            
            # Verify intervention handled thundering herd
            assert result is not None
            assert result.success is True
            
            # Should quarantine one agent to reduce load
            quarantined_agents = quarantine_manager.get_quarantined_agents()
            assert len(quarantined_agents) > 0
            
            # Verify system stabilized
            time.sleep(1.0)
            active_agents = network.get_active_agents()
            assert len(active_agents) >= 5, "Most agents should remain active"
            
        finally:
            network.stop_simulation()
    
    def test_priority_inversion_scenario(self):
        """Test priority inversion scenario and resolution."""
        network = AgentNetwork(agent_count=3)
        
        try:
            agents = network.create_agents()
            
            # Create priority inversion scenario:
            # High priority agent blocked by low priority agent holding resource
            # Medium priority agent prevents low priority from releasing resource
            
            high_priority_agent = agents[0]
            medium_priority_agent = agents[1] 
            low_priority_agent = agents[2]
            
            # Low priority agent holds resource that high priority needs
            low_priority_intention = AgentIntention(
                agent_id=low_priority_agent.agent_id,
                resource_type="database",
                requested_amount=100,
                priority_level=2,
                timestamp=datetime.now()
            )
            
            # High priority agent wants same resource
            high_priority_intention = AgentIntention(
                agent_id=high_priority_agent.agent_id,
                resource_type="database", 
                requested_amount=100,
                priority_level=9,
                timestamp=datetime.now() + timedelta(milliseconds=100)
            )
            
            # Medium priority agent competes for CPU, preventing low priority from finishing
            medium_priority_intention = AgentIntention(
                agent_id=medium_priority_agent.agent_id,
                resource_type="cpu",
                requested_amount=800,  # Uses most CPU
                priority_level=5,
                timestamp=datetime.now() + timedelta(milliseconds=50)
            )
            
            # Set intentions
            low_priority_agent._current_intentions = [low_priority_intention]
            high_priority_agent._current_intentions = [high_priority_intention]
            medium_priority_agent._current_intentions = [medium_priority_intention]
            
            # Pre-allocate database resource to low priority agent
            request = network.resource_manager.process_request(
                type('MockRequest', (), {
                    'agent_id': low_priority_agent.agent_id,
                    'resource_type': 'database',
                    'amount': 100,
                    'priority': 2,
                    'timestamp': datetime.now()
                })()
            )
            assert request.success
            
            network.start_simulation()
            time.sleep(1.5)
            
            # Create priority inversion analysis
            inversion_analysis = ConflictAnalysis(
                risk_score=0.82,
                confidence_level=0.87,
                affected_agents=[agent.agent_id for agent in agents],
                predicted_failure_mode="Priority inversion: high-priority agent blocked by low-priority agent, medium-priority agent preventing resolution",
                nash_equilibrium=None,
                timestamp=datetime.now()
            )
            
            # Process intervention
            result = intervention_engine.process_conflict_analysis(inversion_analysis)
            
            # Verify intervention resolved priority inversion
            assert result is not None
            assert result.success is True
            
            # Should quarantine the medium priority agent causing the inversion
            quarantined_agents = quarantine_manager.get_quarantined_agents()
            assert len(quarantined_agents) > 0
            
            # Verify system can resolve priority correctly
            time.sleep(1.0)
            active_agents = network.get_active_agents()
            assert len(active_agents) >= 2, "High and low priority agents should remain active"
            
        finally:
            network.stop_simulation()





    def test_graceful_degradation_with_kafka_unavailable(self):


        """Test that the system degrades gracefully when Kafka is unavailable."""


        with patch('src.integrations.kafka_client.KafkaMessageBus') as MockKafkaBus:


            mock_kafka_instance = MockKafkaBus.return_value


            mock_kafka_instance.produce.side_effect = KafkaOperationError("Kafka is down")


            mock_kafka_instance.message_buffer = []





            system = ConflictPredictorSystem()


            self.system = system


            


            try:


                system.start_system(agent_count=2)


                time.sleep(1.0)





                system.simulate_conflict_scenario()





                # Verify that produce was called and that the message was buffered


                assert mock_kafka_instance.produce.called


                assert len(mock_kafka_instance.message_buffer) > 0





                # Restore the connection


                mock_kafka_instance.produce.side_effect = None


                mock_kafka_instance._is_connected = True


                mock_kafka_instance._replay_buffer()





                # Verify that the buffer is now empty


                assert len(mock_kafka_instance.message_buffer) == 0





            finally:


                system.stop_system()





if __name__ == "__main__":


    # Run failure scenario tests


    pytest.main([__file__, "-v", "-m", "integration"])

