"""
Unit tests for agent simulation components.
"""
import pytest
import time
import threading
from datetime import datetime
from unittest.mock import Mock, patch

from src.prediction_engine.simulator import SimulatedAgent, ResourceManager, AgentNetwork
from src.prediction_engine.models.core import (
    AgentMessage, ResourceRequest, MessageType, ResourceType
)


class TestSimulatedAgent:
    """Test cases for SimulatedAgent class."""
    
    def test_agent_initialization(self):
        """Test agent is properly initialized."""
        agent = SimulatedAgent("test_agent_001")
        
        assert agent.agent_id == "test_agent_001"
        assert agent.trust_score == 100
        assert not agent.is_quarantined
        assert not agent.is_active
        assert len(agent.current_intentions) == 0
    
    def test_agent_custom_trust_score(self):
        """Test agent initialization with custom trust score."""
        agent = SimulatedAgent("test_agent_002", initial_trust_score=75)
        
        assert agent.agent_id == "test_agent_002"
        assert agent.trust_score == 75
    
    def test_make_resource_request(self):
        """Test agent can make resource requests."""
        agent = SimulatedAgent("test_agent_003")
        mock_resource_manager = Mock()
        mock_resource_manager.process_request.return_value = Mock(success=True)
        agent.set_resource_manager(mock_resource_manager)
        
        request = agent.make_resource_request("cpu", 50)
        
        assert request.agent_id == "test_agent_003"
        assert request.resource_type == "cpu"
        assert request.amount == 50
        assert isinstance(request.timestamp, datetime)
        mock_resource_manager.process_request.assert_called_once()
    
    def test_receive_message(self):
        """Test agent can receive and process messages."""
        agent = SimulatedAgent("test_agent_004")
        
        message = AgentMessage(
            sender_id="other_agent",
            receiver_id="test_agent_004",
            message_type=MessageType.STATUS_UPDATE.value,
            content={"trust_score": 90},
            timestamp=datetime.now()
        )
        
        # Should not raise an exception
        agent.receive_message(message)
    
    def test_quarantine_functionality(self):
        """Test agent quarantine functionality."""
        agent = SimulatedAgent("test_agent_005")
        
        assert not agent.is_quarantined
        
        agent.quarantine()
        assert agent.is_quarantined
        
        agent.release_quarantine()
        assert not agent.is_quarantined
    
    def test_get_current_intentions(self):
        """Test getting current intentions returns a copy."""
        agent = SimulatedAgent("test_agent_006")
        
        intentions = agent.get_current_intentions()
        assert isinstance(intentions, list)
        assert len(intentions) == 0
        
        # Modifying returned list should not affect agent's intentions
        intentions.append("fake_intention")
        assert len(agent.get_current_intentions()) == 0


class TestResourceManager:
    """Test cases for ResourceManager class."""
    
    def test_resource_manager_initialization(self):
        """Test resource manager is properly initialized."""
        manager = ResourceManager()
        
        # Check all resource types are initialized
        for resource_type in ResourceType:
            status = manager.get_resource_status(resource_type.value)
            assert status.total_capacity == 1000
            assert status.current_usage == 0
    
    def test_successful_resource_allocation(self):
        """Test successful resource allocation."""
        manager = ResourceManager()
        
        request = ResourceRequest(
            agent_id="test_agent",
            resource_type="cpu",
            amount=100,
            priority=5,
            timestamp=datetime.now()
        )
        
        result = manager.process_request(request)
        
        assert result.success
        assert result.allocated_amount == 100
        assert "granted in full" in result.reason.lower()
        
        # Check resource usage updated
        status = manager.get_resource_status("cpu")
        assert status.current_usage == 100
    
    def test_partial_resource_allocation(self):
        """Test partial resource allocation when insufficient resources."""
        manager = ResourceManager()
        
        # First request uses most resources
        request1 = ResourceRequest(
            agent_id="agent1",
            resource_type="memory",
            amount=950,
            priority=5,
            timestamp=datetime.now()
        )
        manager.process_request(request1)
        
        # Second request should get partial allocation
        request2 = ResourceRequest(
            agent_id="agent2",
            resource_type="memory",
            amount=100,
            priority=5,
            timestamp=datetime.now()
        )
        
        result = manager.process_request(request2)
        
        assert result.success
        assert result.allocated_amount == 50  # Only 50 remaining
        assert "partial" in result.reason.lower()
    
    def test_failed_resource_allocation(self):
        """Test failed resource allocation when no resources available."""
        manager = ResourceManager()
        
        # Use all resources
        request1 = ResourceRequest(
            agent_id="agent1",
            resource_type="storage",
            amount=1000,
            priority=5,
            timestamp=datetime.now()
        )
        manager.process_request(request1)
        
        # Second request should fail
        request2 = ResourceRequest(
            agent_id="agent2",
            resource_type="storage",
            amount=50,
            priority=5,
            timestamp=datetime.now()
        )
        
        result = manager.process_request(request2)
        
        assert not result.success
        assert result.allocated_amount == 0
        assert "no resources available" in result.reason.lower()
    
    def test_contention_detection(self):
        """Test resource contention detection."""
        manager = ResourceManager()
        
        # Use all resources to force contention
        request1 = ResourceRequest(
            agent_id="agent1",
            resource_type="network",
            amount=1000,
            priority=5,
            timestamp=datetime.now()
        )
        manager.process_request(request1)
        
        # Create competing requests
        request2 = ResourceRequest(
            agent_id="agent2",
            resource_type="network",
            amount=100,
            priority=5,
            timestamp=datetime.now()
        )
        request3 = ResourceRequest(
            agent_id="agent3",
            resource_type="network",
            amount=200,
            priority=5,
            timestamp=datetime.now()
        )
        
        manager.process_request(request2)
        manager.process_request(request3)
        
        contention_events = manager.detect_contention()
        
        assert len(contention_events) == 1
        event = contention_events[0]
        assert event.resource_type == "network"
        assert "agent2" in event.competing_agents
        assert "agent3" in event.competing_agents
        assert event.severity > 0
    
    def test_unknown_resource_type(self):
        """Test handling of unknown resource types."""
        manager = ResourceManager()
        
        request = ResourceRequest(
            agent_id="test_agent",
            resource_type="unknown_resource",
            amount=50,
            priority=5,
            timestamp=datetime.now()
        )
        
        result = manager.process_request(request)
        
        assert not result.success
        assert result.allocated_amount == 0
        assert "unknown resource type" in result.reason.lower()


class TestAgentNetwork:
    """Test cases for AgentNetwork class."""
    
    def test_agent_network_initialization(self):
        """Test agent network is properly initialized."""
        network = AgentNetwork(agent_count=5)
        
        assert network.agent_count == 5
        assert len(network.agents) == 0
        assert not network.is_running
        assert network.resource_manager is not None
    
    def test_create_agents(self):
        """Test creating agents in the network."""
        network = AgentNetwork(agent_count=3)
        
        agents = network.create_agents()
        
        assert len(agents) == 3
        assert len(network.agents) == 3
        
        # Check agent IDs are properly formatted
        expected_ids = ["agent_001", "agent_002", "agent_003"]
        actual_ids = [agent.agent_id for agent in agents]
        assert actual_ids == expected_ids
        
        # Check agents have resource manager and network set
        for agent in agents:
            assert agent.resource_manager is not None
    
    def test_create_agents_invalid_count(self):
        """Test creating agents with invalid count raises error."""
        with pytest.raises(ValueError):
            AgentNetwork(agent_count=-1)
    
    def test_get_active_agents(self):
        """Test getting active agents."""
        network = AgentNetwork(agent_count=3)
        agents = network.create_agents()
        
        # Initially no agents are active
        active_agents = network.get_active_agents()
        assert len(active_agents) == 0
        
        # Start one agent
        agents[0].start()
        time.sleep(0.1)  # Give thread time to start
        
        active_agents = network.get_active_agents()
        assert len(active_agents) == 1
        assert active_agents[0].agent_id == "agent_001"
        
        # Clean up
        agents[0].stop()
    
    def test_quarantine_operations(self):
        """Test quarantine operations on agents."""
        network = AgentNetwork(agent_count=2)
        agents = network.create_agents()
        
        # Test quarantine
        result = network.quarantine_agent("agent_001")
        assert result
        assert agents[0].is_quarantined
        
        # Test release quarantine
        result = network.release_agent_quarantine("agent_001")
        assert result
        assert not agents[0].is_quarantined
        
        # Test quarantine non-existent agent
        result = network.quarantine_agent("non_existent_agent")
        assert not result
    
    def test_get_all_intentions(self):
        """Test getting all intentions from agents."""
        network = AgentNetwork(agent_count=2)
        agents = network.create_agents()
        
        # Initially no intentions
        intentions = network.get_all_intentions()
        assert len(intentions) == 0
        
        # Add some mock intentions and start the agent to make it active
        from src.prediction_engine.models.core import AgentIntention
        intention1 = AgentIntention(
            agent_id="agent_001",
            resource_type="cpu",
            requested_amount=50,
            priority_level=5,
            timestamp=datetime.now()
        )
        agents[0].current_intentions.append(intention1)
        agents[0].start()  # Make agent active
        time.sleep(0.1)  # Give thread time to start
        
        intentions = network.get_all_intentions()
        # Should have at least our manually added intention
        assert len(intentions) >= 1
        # Check that our manually added intention is present
        manual_intentions = [i for i in intentions if i.requested_amount == 50]
        assert len(manual_intentions) == 1
        assert manual_intentions[0].agent_id == "agent_001"
        
        # Clean up
        agents[0].stop()
    
    @patch('time.sleep')  # Mock sleep to speed up test
    def test_simulation_lifecycle(self, mock_sleep):
        """Test starting and stopping simulation."""
        network = AgentNetwork(agent_count=3)
        
        # Start simulation (should create agents automatically)
        network.start_simulation()
        
        assert network.is_running
        assert len(network.agents) == 3
        
        # Give threads time to start
        time.sleep(0.1)
        
        # Stop simulation
        network.stop_simulation()
        
        assert not network.is_running
        
        # All agents should be stopped
        for agent in network.agents:
            assert not agent.is_active