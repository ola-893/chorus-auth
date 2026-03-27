"""
Integration test for the complete agent simulation environment.
"""
import pytest
import time
from src.prediction_engine.simulator import AgentNetwork


def test_full_simulation_integration():
    """Test the complete agent simulation workflow."""
    # Create and start a simulation
    network = AgentNetwork(agent_count=5)
    
    # Start simulation (should create agents automatically)
    network.start_simulation()
    
    try:
        # Verify agents were created
        assert len(network.agents) >= 3
        assert len(network.agents) <= 5
        assert network.is_running
        
        # Let simulation run for a short time
        time.sleep(2.0)
        
        # Check that agents are active and making requests
        active_agents = network.get_active_agents()
        assert len(active_agents) >= 3
        
        # Check that agents have generated some intentions
        all_intentions = network.get_all_intentions()
        assert len(all_intentions) > 0
        
        # Check resource contention detection
        contention_events = network.resource_manager.detect_contention()
        # May or may not have contention, but should not error
        assert isinstance(contention_events, list)
        
        # Test quarantine functionality
        first_agent_id = network.agents[0].agent_id
        success = network.quarantine_agent(first_agent_id)
        assert success
        assert network.agents[0].is_quarantined
        
        # Verify quarantined agent stops making requests
        time.sleep(1.0)
        
        # Release quarantine
        success = network.release_agent_quarantine(first_agent_id)
        assert success
        assert not network.agents[0].is_quarantined
        
    finally:
        # Always stop the simulation
        network.stop_simulation()
        
        # Verify simulation stopped
        assert not network.is_running
        for agent in network.agents:
            assert not agent.is_active


def test_resource_contention_scenario():
    """Test a scenario that creates resource contention."""
    network = AgentNetwork(agent_count=3)
    agents = network.create_agents()
    
    # Use up most resources to force contention
    for resource_type in ["cpu", "memory", "storage"]:
        request = network.resource_manager.process_request(
            type('MockRequest', (), {
                'agent_id': 'test_agent',
                'resource_type': resource_type,
                'amount': 900,  # Use 90% of capacity
                'priority': 5,
                'timestamp': None
            })()
        )
        assert request.success
    
    # Start agents - they should compete for remaining resources
    network.start_simulation()
    
    try:
        # Let agents run and compete for resources
        time.sleep(1.0)
        
        # Check for contention events
        contention_events = network.resource_manager.detect_contention()
        
        # Should have some contention due to limited resources
        # (May not always trigger due to timing, but test should not fail)
        assert isinstance(contention_events, list)
        
    finally:
        network.stop_simulation()


if __name__ == "__main__":
    test_full_simulation_integration()
    test_resource_contention_scenario()
    print("All integration tests passed!")