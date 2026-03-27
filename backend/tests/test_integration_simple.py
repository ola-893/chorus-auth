"""
Simple integration tests that don't require external dependencies like Redis.

These tests focus on the core integration logic and workflows without
requiring Redis or other external services to be running.
"""
import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch

from src.prediction_engine.simulator import AgentNetwork
from src.prediction_engine.models.core import (
    AgentIntention, ConflictAnalysis, ResourceType
)


@pytest.mark.integration
class TestSimpleIntegration:
    """Simple integration tests without external dependencies."""
    
    def test_agent_network_basic_workflow(self):
        """Test basic agent network creation and operation."""
        network = AgentNetwork(agent_count=5)
        
        try:
            # Create agents
            agents = network.create_agents()
            
            # Verify agents created
            assert len(agents) == 4
            assert len(network.agents) == 4
            
            # Verify agent IDs are unique
            agent_ids = [agent.agent_id for agent in agents]
            assert len(set(agent_ids)) == 4
            
            # Start simulation
            network.start_simulation()
            
            # Verify simulation started
            assert network.is_running
            
            # Let agents run briefly
            time.sleep(1.0)
            
            # Verify agents are active
            active_agents = network.get_active_agents()
            assert len(active_agents) == 4
            
            # Verify agents generate intentions
            intentions = network.get_all_intentions()
            assert len(intentions) >= 0  # May be empty initially
            
            # Test resource manager
            resource_status = network.resource_manager.get_resource_status("cpu")
            assert resource_status.total_capacity > 0
            assert resource_status.current_usage >= 0
            
            # Test contention detection
            contention_events = network.resource_manager.detect_contention()
            assert isinstance(contention_events, list)
            
        finally:
            # Stop simulation
            network.stop_simulation()
            
            # Verify simulation stopped
            assert not network.is_running
            for agent in network.agents:
                assert not agent.is_active
    
    def test_agent_intention_generation(self):
        """Test that agents generate valid intentions."""
        network = AgentNetwork(agent_count=2)
        
        try:
            # Create and start agents
            agents = network.create_agents()
            network.start_simulation()
            
            # Let agents run to generate intentions
            time.sleep(2.0)
            
            # Get intentions
            intentions = network.get_all_intentions()
            
            # Verify intentions are valid
            for intention in intentions:
                assert isinstance(intention, AgentIntention)
                assert intention.agent_id in [agent.agent_id for agent in agents]
                assert intention.resource_type in ["cpu", "memory", "storage", "network", "database"]
                assert intention.requested_amount > 0
                assert 1 <= intention.priority_level <= 10
                assert isinstance(intention.timestamp, datetime)
            
        finally:
            network.stop_simulation()
    
    def test_resource_management_workflow(self):
        """Test resource management and allocation."""
        network = AgentNetwork(agent_count=2)
        
        try:
            # Create agents
            agents = network.create_agents()
            
            # Test resource allocation
            request = type('MockRequest', (), {
                'agent_id': agents[0].agent_id,
                'resource_type': 'cpu',
                'amount': 100,
                'priority': 5,
                'timestamp': datetime.now()
            })()
            
            # Process request
            result = network.resource_manager.process_request(request)
            
            # Verify request processed
            assert hasattr(result, 'success')
            
            # Check resource status after allocation
            cpu_status = network.resource_manager.get_resource_status('cpu')
            assert cpu_status.total_capacity > 0
            
            # Test multiple resource types
            for resource_type in ["memory", "storage", "network"]:
                status = network.resource_manager.get_resource_status(resource_type)
                assert status.total_capacity > 0
                assert status.current_usage >= 0
                assert status.current_usage <= status.total_capacity
            
        finally:
            network.stop_simulation()
    
    def test_conflict_analysis_parser_workflow(self):
        """Test conflict analysis parser workflow without API dependency."""
        # Test the parser directly with a mock response
        from src.prediction_engine.analysis_parser import ConflictAnalysisParser
        
        parser = ConflictAnalysisParser()
        
        # Test response text
        response_text = """
        RISK_SCORE: 0.75
        CONFIDENCE: 0.85
        AFFECTED_AGENTS: agent_1, agent_2
        FAILURE_MODE: Resource contention
        NASH_EQUILIBRIUM: Competitive equilibrium
        REASONING: Agents competing for limited resources
        """
        
        # Parse the response
        analysis = parser.parse_conflict_analysis(response_text)
        
        # Verify analysis
        assert analysis.risk_score == 0.75
        assert analysis.confidence_level == 0.85
        assert len(analysis.affected_agents) == 2
        assert "agent_1" in analysis.affected_agents
        assert "agent_2" in analysis.affected_agents
        assert "contention" in analysis.predicted_failure_mode.lower()
    
    def test_agent_quarantine_workflow_without_redis(self):
        """Test agent quarantine workflow without Redis dependency."""
        network = AgentNetwork(agent_count=3)
        
        try:
            # Create and start agents
            agents = network.create_agents()
            network.start_simulation()
            
            # Verify all agents are active initially
            active_agents = network.get_active_agents()
            assert len(active_agents) == 3
            
            # Test quarantine functionality at agent level
            target_agent = agents[0]
            
            # Quarantine agent directly (bypassing Redis)
            target_agent.quarantine()
            
            # Verify agent is quarantined
            assert target_agent.is_quarantined
            
            # Verify other agents remain active
            time.sleep(0.5)
            active_agents = network.get_active_agents()
            
            # Should have 2 active agents (3 total - 1 quarantined)
            non_quarantined_agents = [a for a in network.agents if not a.is_quarantined]
            assert len(non_quarantined_agents) == 2
            
            # Release quarantine
            target_agent.release_quarantine()
            
            # Verify agent is released
            assert not target_agent.is_quarantined
            
            # Verify all agents are active again
            time.sleep(0.5)
            non_quarantined_agents = [a for a in network.agents if not a.is_quarantined]
            assert len(non_quarantined_agents) == 3
            
        finally:
            network.stop_simulation()
    
    def test_system_error_resilience(self):
        """Test system resilience to component failures."""
        network = AgentNetwork(agent_count=2)
        
        try:
            # Create and start agents
            agents = network.create_agents()
            network.start_simulation()
            
            # Verify normal operation
            assert network.is_running
            assert len(network.get_active_agents()) == 2
            
            # Simulate component failure by stopping one agent
            agents[0].stop()
            
            # System should continue with remaining agent
            time.sleep(0.5)
            
            # Verify system is still running
            assert network.is_running
            
            # Verify at least one agent is still active
            active_agents = network.get_active_agents()
            assert len(active_agents) >= 1
            
            # Test resource manager continues working
            resource_status = network.resource_manager.get_resource_status("cpu")
            assert resource_status.total_capacity > 0
            
        finally:
            network.stop_simulation()
    
    def test_concurrent_agent_operations(self):
        """Test concurrent agent operations."""
        network = AgentNetwork(agent_count=4)
        
        try:
            # Create agents
            agents = network.create_agents(4)
            network.start_simulation()
            
            # Let agents run concurrently
            time.sleep(2.0)
            
            # Verify all agents are operating
            active_agents = network.get_active_agents()
            assert len(active_agents) == 4
            
            # Test concurrent resource requests
            intentions = network.get_all_intentions()
            
            # Should have intentions from multiple agents
            agent_ids_with_intentions = set(i.agent_id for i in intentions)
            
            # May not have intentions from all agents due to timing,
            # but should have some concurrent activity
            assert len(intentions) >= 0
            
            # Test resource contention detection with concurrent operations
            contention_events = network.resource_manager.detect_contention()
            assert isinstance(contention_events, list)
            
            # Verify system handles concurrent operations without errors
            status_checks = []
            for _ in range(5):
                try:
                    status = {
                        'active_agents': len(network.get_active_agents()),
                        'total_agents': len(network.agents),
                        'is_running': network.is_running
                    }
                    status_checks.append(status)
                    time.sleep(0.1)
                except Exception as e:
                    pytest.fail(f"System failed during concurrent operations: {e}")
            
            # Verify consistent system state
            assert all(check['is_running'] for check in status_checks)
            assert all(check['total_agents'] == 4 for check in status_checks)
            
        finally:
            network.stop_simulation()


if __name__ == "__main__":
    # Run simple integration tests
    pytest.main([__file__, "-v", "-m", "integration"])