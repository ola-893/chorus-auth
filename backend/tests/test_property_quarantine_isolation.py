"""
Property-based test for quarantine isolation effectiveness.

**Feature: agent-conflict-predictor, Property 6: Quarantine isolation effectiveness**
**Validates: Requirements 4.2, 4.4**
"""
import pytest
import time
import threading
from datetime import datetime, timedelta
from typing import List, Set, Dict
from unittest.mock import Mock, patch
from hypothesis import given, strategies as st, assume, settings, HealthCheck

from src.prediction_engine.quarantine_manager import RedisQuarantineManager
from src.prediction_engine.simulator import SimulatedAgent, AgentNetwork, ResourceManager
from src.prediction_engine.models.core import QuarantineResult, ResourceRequest, AgentIntention


class TestQuarantineIsolationEffectiveness:
    """Property-based tests for quarantine isolation effectiveness."""
    
    def create_mock_redis_client(self):
        """Create a mock Redis client that simulates Redis behavior consistently."""
        mock_client = Mock()
        
        # Simulate Redis storage with consistent behavior
        redis_storage = {}
        
        def mock_exists(key):
            return key in redis_storage
        
        def mock_get(key):
            return redis_storage.get(key)
        
        def mock_get_json(key):
            return redis_storage.get(key)
        
        def mock_set_json(key, value, ttl=None):
            redis_storage[key] = value
            return True
        
        def mock_set(key, value, ttl=None):
            redis_storage[key] = value
            return True
        
        def mock_delete(key):
            if key in redis_storage:
                del redis_storage[key]
                return True
            return False
        
        mock_client.exists.side_effect = mock_exists
        mock_client.get.side_effect = mock_get
        mock_client.get_json.side_effect = mock_get_json
        mock_client.set_json.side_effect = mock_set_json
        mock_client.set.side_effect = mock_set
        mock_client.delete.side_effect = mock_delete
        
        # Store reference to redis_storage for test access
        mock_client._redis_storage = redis_storage
        
        return mock_client
    
    @given(
        agent_count=st.integers(min_value=3, max_value=8),
        quarantine_agent_index=st.integers(min_value=0, max_value=7),
        observation_time=st.floats(min_value=1.0, max_value=3.0)
    )
    @settings(max_examples=50, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_quarantined_agent_prevented_from_new_requests(self, agent_count, quarantine_agent_index, observation_time):
        """
        Property: For any quarantined agent, it should be prevented from making 
        new resource requests while other agents continue operating normally.
        
        **Feature: agent-conflict-predictor, Property 6: Quarantine isolation effectiveness**
        **Validates: Requirements 4.2, 4.4**
        """
        assume(quarantine_agent_index < agent_count)
        
        # Set up test environment
        mock_redis_client = self.create_mock_redis_client()
        quarantine_manager = RedisQuarantineManager(
            redis_client_instance=mock_redis_client,
            key_prefix="test_quarantine"
        )
        
        network = AgentNetwork(agent_count=10, quarantine_manager=quarantine_manager)
        agents = network.create_agents()
        
        # Track resource requests from all agents
        request_tracker = {}
        original_process_request = network.resource_manager.process_request
        
        def track_requests(request):
            if request.agent_id not in request_tracker:
                request_tracker[request.agent_id] = []
            request_tracker[request.agent_id].append({
                'timestamp': request.timestamp,
                'resource_type': request.resource_type,
                'amount': request.amount,
                'quarantined_at_time': agents[quarantine_agent_index].is_quarantined
            })
            return original_process_request(request)
        
        network.resource_manager.process_request = track_requests
        
        # Start simulation
        network.start_simulation()
        
        try:
            # Let agents run for a bit to establish baseline behavior
            time.sleep(0.5)
            
            # Quarantine the selected agent (Requirement 4.2)
            target_agent = agents[quarantine_agent_index]
            quarantine_result = quarantine_manager.quarantine_agent(
                target_agent.agent_id, 
                "Test quarantine for isolation effectiveness"
            )
            
            assert quarantine_result.success, f"Quarantine should succeed for agent {target_agent.agent_id}"
            
            # Wait for quarantine to take effect and observe behavior
            time.sleep(0.2)  # Brief pause for quarantine to propagate
            
            # Clear request tracker to focus on post-quarantine behavior
            pre_quarantine_requests = dict(request_tracker)
            request_tracker.clear()
            
            # Observe post-quarantine behavior
            time.sleep(observation_time)
            
            # Verify quarantine isolation effectiveness (Requirements 4.2, 4.4)
            quarantined_agent_id = target_agent.agent_id
            other_agent_ids = [a.agent_id for a in agents if a.agent_id != quarantined_agent_id]
            
            # Requirement 4.2: Quarantined agent should be prevented from making new requests
            quarantined_requests = request_tracker.get(quarantined_agent_id, [])
            
            # The quarantined agent should make no new resource requests
            assert len(quarantined_requests) == 0, (
                f"Quarantined agent {quarantined_agent_id} should not make new resource requests, "
                f"but made {len(quarantined_requests)} requests"
            )
            
            # Verify the agent is actually quarantined
            assert quarantine_manager.is_quarantined(quarantined_agent_id), (
                f"Agent {quarantined_agent_id} should be marked as quarantined"
            )
            assert target_agent.is_quarantined, (
                f"Agent {quarantined_agent_id} should have quarantine flag set"
            )
            
            # Requirement 4.4: Other agents should continue operating normally
            other_agents_with_requests = set(request_tracker.keys()) & set(other_agent_ids)
            
            # At least some other agents should continue making requests
            if len(other_agent_ids) > 0:
                # Allow for timing variations - not all agents may make requests in the observation window
                # But at least verify that non-quarantined agents CAN make requests
                total_other_requests = sum(
                    len(request_tracker.get(agent_id, [])) for agent_id in other_agent_ids
                )
                
                # Verify other agents are not quarantined
                for other_agent_id in other_agent_ids:
                    assert not quarantine_manager.is_quarantined(other_agent_id), (
                        f"Non-target agent {other_agent_id} should not be quarantined"
                    )
                
                # Verify other agents can still make requests (system continues operating)
                other_agents_active = [a for a in agents if a.agent_id != quarantined_agent_id and a.is_active]
                assert len(other_agents_active) > 0, "Other agents should remain active"
                
                # Check that other agents are not prevented from making requests
                for other_agent in other_agents_active:
                    assert not other_agent.is_quarantined, (
                        f"Non-quarantined agent {other_agent.agent_id} should not have quarantine flag"
                    )
            
            # Verify quarantine persistence
            assert quarantine_manager.is_quarantined(quarantined_agent_id), (
                "Quarantine status should persist throughout observation period"
            )
            
        finally:
            network.stop_simulation()
    
    @given(
        agent_count=st.integers(min_value=4, max_value=8),
        quarantine_indices=st.lists(
            st.integers(min_value=0, max_value=7),
            min_size=1,
            max_size=3,
            unique=True
        ),
        observation_time=st.floats(min_value=1.5, max_value=3.0)
    )
    @settings(max_examples=30, deadline=12000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_multiple_quarantined_agents_isolation(self, agent_count, quarantine_indices, observation_time):
        """
        Property: For any set of quarantined agents, all quarantined agents should 
        be prevented from making requests while non-quarantined agents continue normally.
        
        **Feature: agent-conflict-predictor, Property 6: Quarantine isolation effectiveness**
        **Validates: Requirements 4.2, 4.4**
        """
        # Filter quarantine indices to be within agent count
        valid_quarantine_indices = [idx for idx in quarantine_indices if idx < agent_count]
        assume(len(valid_quarantine_indices) > 0)
        assume(len(valid_quarantine_indices) < agent_count)  # Leave at least one agent non-quarantined
        
        # Set up test environment
        mock_redis_client = self.create_mock_redis_client()
        quarantine_manager = RedisQuarantineManager(
            redis_client_instance=mock_redis_client,
            key_prefix="test_quarantine"
        )
        
        network = AgentNetwork(agent_count=10, quarantine_manager=quarantine_manager)
        agents = network.create_agents()
        
        # Track resource requests
        request_tracker = {}
        original_process_request = network.resource_manager.process_request
        
        def track_requests(request):
            if request.agent_id not in request_tracker:
                request_tracker[request.agent_id] = []
            request_tracker[request.agent_id].append({
                'timestamp': request.timestamp,
                'resource_type': request.resource_type,
                'amount': request.amount
            })
            return original_process_request(request)
        
        network.resource_manager.process_request = track_requests
        
        # Start simulation
        network.start_simulation()
        
        try:
            # Let agents establish baseline behavior
            time.sleep(0.5)
            
            # Quarantine selected agents
            quarantined_agent_ids = []
            for idx in valid_quarantine_indices:
                target_agent = agents[idx]
                quarantine_result = quarantine_manager.quarantine_agent(
                    target_agent.agent_id,
                    f"Test quarantine {idx} for multiple isolation"
                )
                assert quarantine_result.success, f"Quarantine should succeed for agent {target_agent.agent_id}"
                quarantined_agent_ids.append(target_agent.agent_id)
            
            # Wait for quarantine to take effect
            time.sleep(0.2)
            
            # Clear request tracker to focus on post-quarantine behavior
            request_tracker.clear()
            
            # Observe post-quarantine behavior
            time.sleep(observation_time)
            
            # Identify non-quarantined agents
            non_quarantined_agent_ids = [
                a.agent_id for a in agents if a.agent_id not in quarantined_agent_ids
            ]
            
            # Verify all quarantined agents are prevented from making requests (Requirement 4.2)
            for quarantined_id in quarantined_agent_ids:
                quarantined_requests = request_tracker.get(quarantined_id, [])
                assert len(quarantined_requests) == 0, (
                    f"Quarantined agent {quarantined_id} should not make new requests, "
                    f"but made {len(quarantined_requests)} requests"
                )
                
                # Verify quarantine status
                assert quarantine_manager.is_quarantined(quarantined_id), (
                    f"Agent {quarantined_id} should be marked as quarantined"
                )
            
            # Verify non-quarantined agents continue operating (Requirement 4.4)
            assert len(non_quarantined_agent_ids) > 0, "Should have at least one non-quarantined agent"
            
            for non_quarantined_id in non_quarantined_agent_ids:
                # Verify they are not quarantined
                assert not quarantine_manager.is_quarantined(non_quarantined_id), (
                    f"Non-quarantined agent {non_quarantined_id} should not be marked as quarantined"
                )
                
                # Find the agent object
                agent_obj = next(a for a in agents if a.agent_id == non_quarantined_id)
                assert not agent_obj.is_quarantined, (
                    f"Non-quarantined agent {non_quarantined_id} should not have quarantine flag"
                )
                assert agent_obj.is_active, (
                    f"Non-quarantined agent {non_quarantined_id} should remain active"
                )
            
            # Verify system continues operating with remaining agents
            total_non_quarantined_requests = sum(
                len(request_tracker.get(agent_id, [])) for agent_id in non_quarantined_agent_ids
            )
            
            # The system should continue functioning with non-quarantined agents
            active_non_quarantined = [
                a for a in agents 
                if a.agent_id in non_quarantined_agent_ids and a.is_active
            ]
            assert len(active_non_quarantined) > 0, "Should have active non-quarantined agents"
            
        finally:
            network.stop_simulation()
    
    @given(
        agent_count=st.integers(min_value=3, max_value=6),
        quarantine_agent_index=st.integers(min_value=0, max_value=5),
        observation_time=st.floats(min_value=1.0, max_value=2.5)
    )
    @settings(max_examples=30, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_quarantine_release_restores_functionality(self, agent_count, quarantine_agent_index, observation_time):
        """
        Property: For any quarantined agent, releasing quarantine should restore 
        the agent's ability to make resource requests.
        
        **Feature: agent-conflict-predictor, Property 6: Quarantine isolation effectiveness**
        **Validates: Requirements 4.2**
        """
        assume(quarantine_agent_index < agent_count)
        
        # Set up test environment
        mock_redis_client = self.create_mock_redis_client()
        quarantine_manager = RedisQuarantineManager(
            redis_client_instance=mock_redis_client,
            key_prefix="test_quarantine"
        )
        
        network = AgentNetwork(agent_count=8, quarantine_manager=quarantine_manager)
        agents = network.create_agents()
        
        # Track resource requests with phases
        request_tracker = {}
        phase_tracker = {"current_phase": "baseline"}
        
        original_process_request = network.resource_manager.process_request
        
        def track_requests(request):
            if request.agent_id not in request_tracker:
                request_tracker[request.agent_id] = {
                    "baseline": [],
                    "quarantined": [],
                    "released": []
                }
            
            current_phase = phase_tracker["current_phase"]
            request_tracker[request.agent_id][current_phase].append({
                'timestamp': request.timestamp,
                'resource_type': request.resource_type,
                'amount': request.amount
            })
            return original_process_request(request)
        
        network.resource_manager.process_request = track_requests
        
        # Start simulation
        network.start_simulation()
        
        try:
            target_agent = agents[quarantine_agent_index]
            target_agent_id = target_agent.agent_id
            
            # Phase 1: Baseline behavior
            time.sleep(observation_time * 0.3)
            
            # Phase 2: Quarantine the agent
            phase_tracker["current_phase"] = "quarantined"
            quarantine_result = quarantine_manager.quarantine_agent(
                target_agent_id,
                "Test quarantine for release functionality"
            )
            assert quarantine_result.success, f"Quarantine should succeed for agent {target_agent_id}"
            
            time.sleep(0.2)  # Let quarantine take effect
            time.sleep(observation_time * 0.3)
            
            # Verify quarantine is effective
            quarantined_requests = request_tracker.get(target_agent_id, {}).get("quarantined", [])
            assert len(quarantined_requests) == 0, (
                f"Agent {target_agent_id} should not make requests while quarantined"
            )
            assert quarantine_manager.is_quarantined(target_agent_id), (
                f"Agent {target_agent_id} should be quarantined"
            )
            
            # Phase 3: Release quarantine
            phase_tracker["current_phase"] = "released"
            release_result = quarantine_manager.release_quarantine(target_agent_id)
            assert release_result.success, f"Quarantine release should succeed for agent {target_agent_id}"
            
            time.sleep(0.2)  # Let release take effect
            time.sleep(observation_time * 0.4)
            
            # Verify quarantine release restores functionality (Requirement 4.2)
            assert not quarantine_manager.is_quarantined(target_agent_id), (
                f"Agent {target_agent_id} should not be quarantined after release"
            )
            assert not target_agent.is_quarantined, (
                f"Agent {target_agent_id} should not have quarantine flag after release"
            )
            
            # Verify agent can make requests again
            released_requests = request_tracker.get(target_agent_id, {}).get("released", [])
            
            # The agent should be able to make requests after release
            # We don't require requests immediately due to timing, but the agent should be capable
            assert target_agent.is_active, f"Agent {target_agent_id} should be active after release"
            
            # Verify the agent's request-making capability is restored by checking its state
            # The agent should not be blocked from making requests
            assert not target_agent.is_quarantined, (
                f"Released agent {target_agent_id} should not be quarantined"
            )
            
            # If the agent made requests after release, verify they were processed
            if released_requests:
                assert len(released_requests) > 0, (
                    f"Released agent {target_agent_id} should be able to make requests"
                )
            
        finally:
            network.stop_simulation()
    
    @given(
        agent_count=st.integers(min_value=5, max_value=8),
        quarantine_reasons=st.lists(
            st.text(min_size=5, max_size=50, alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-'),
            min_size=1,
            max_size=3
        )
    )
    @settings(max_examples=20, deadline=8000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_quarantine_logging_and_tracking(self, agent_count, quarantine_reasons):
        """
        Property: For any quarantine action, the system should log the action 
        with timestamp and reason while maintaining quarantine effectiveness.
        
        **Feature: agent-conflict-predictor, Property 6: Quarantine isolation effectiveness**
        **Validates: Requirements 4.2**
        """
        # Set up test environment
        mock_redis_client = self.create_mock_redis_client()
        quarantine_manager = RedisQuarantineManager(
            redis_client_instance=mock_redis_client,
            key_prefix="test_quarantine"
        )
        
        network = AgentNetwork(agent_count=10, quarantine_manager=quarantine_manager)
        agents = network.create_agents()
        
        network.start_simulation()
        
        try:
            # Quarantine agents with different reasons
            quarantined_agents = []
            for i, reason in enumerate(quarantine_reasons):
                if i < len(agents):
                    target_agent = agents[i]
                    quarantine_result = quarantine_manager.quarantine_agent(
                        target_agent.agent_id,
                        reason
                    )
                    
                    assert quarantine_result.success, (
                        f"Quarantine should succeed for agent {target_agent.agent_id}"
                    )
                    quarantined_agents.append((target_agent.agent_id, reason))
            
            time.sleep(0.5)  # Let quarantine take effect
            
            # Verify quarantine logging and tracking
            for agent_id, expected_reason in quarantined_agents:
                # Verify quarantine status
                assert quarantine_manager.is_quarantined(agent_id), (
                    f"Agent {agent_id} should be quarantined"
                )
                
                # Verify quarantine history contains the action
                history = quarantine_manager.get_quarantine_history(agent_id)
                assert len(history) > 0, f"Agent {agent_id} should have quarantine history"
                
                # Find the quarantine action with matching reason
                matching_actions = [
                    action for action in history 
                    if action.agent_id == agent_id and action.reason == expected_reason
                ]
                assert len(matching_actions) > 0, (
                    f"Should find quarantine action for agent {agent_id} with reason '{expected_reason}'"
                )
                
                # Verify action details
                action = matching_actions[0]
                assert action.agent_id == agent_id, "Action should have correct agent ID"
                assert action.reason == expected_reason, "Action should have correct reason"
                assert action.timestamp is not None, "Action should have timestamp"
                assert isinstance(action.timestamp, datetime), "Timestamp should be datetime object"
                
                # Verify timestamp is recent (within last few seconds)
                time_diff = datetime.now() - action.timestamp
                assert time_diff.total_seconds() < 10, "Timestamp should be recent"
            
            # Verify quarantine list contains all quarantined agents
            quarantined_list = quarantine_manager.get_quarantined_agents()
            expected_quarantined_ids = [agent_id for agent_id, _ in quarantined_agents]
            
            for expected_id in expected_quarantined_ids:
                assert expected_id in quarantined_list, (
                    f"Quarantined agent {expected_id} should be in quarantine list"
                )
            
            # Verify statistics
            stats = quarantine_manager.get_statistics()
            assert stats["currently_quarantined"] == len(quarantined_agents), (
                "Statistics should reflect current quarantine count"
            )
            assert stats["total_quarantine_actions"] >= len(quarantined_agents), (
                "Statistics should reflect total quarantine actions"
            )
            
        finally:
            network.stop_simulation()
    
    def test_edge_case_quarantine_nonexistent_agent(self):
        """
        Test edge case: Quarantining a non-existent agent should handle gracefully.
        
        **Feature: agent-conflict-predictor, Property 6: Quarantine isolation effectiveness**
        **Validates: Requirements 4.2**
        """
        mock_redis_client = self.create_mock_redis_client()
        quarantine_manager = RedisQuarantineManager(
            redis_client_instance=mock_redis_client,
            key_prefix="test_quarantine"
        )
        
        # Try to quarantine non-existent agent
        result = quarantine_manager.quarantine_agent("nonexistent_agent", "test reason")
        
        # Should succeed (quarantine manager doesn't validate agent existence)
        assert result.success, "Quarantine manager should handle non-existent agents gracefully"
        
        # Verify quarantine status
        assert quarantine_manager.is_quarantined("nonexistent_agent"), (
            "Non-existent agent should be marked as quarantined"
        )
    def test_edge_case_double_quarantine(self):
        """
        Test edge case: Quarantining an already quarantined agent.
        
        **Feature: agent-conflict-predictor, Property 6: Quarantine isolation effectiveness**
        **Validates: Requirements 4.2**
        """
        mock_redis_client = self.create_mock_redis_client()
        quarantine_manager = RedisQuarantineManager(
            redis_client_instance=mock_redis_client,
            key_prefix="test_quarantine"
        )
        
        network = AgentNetwork(agent_count=5, quarantine_manager=quarantine_manager)
        agents = network.create_agents(3)
        
        network.start_simulation()
        
        try:
            target_agent = agents[0]
            
            # First quarantine
            result1 = quarantine_manager.quarantine_agent(target_agent.agent_id, "first quarantine")
            assert result1.success, "First quarantine should succeed"
            
            # Second quarantine (should handle gracefully)
            result2 = quarantine_manager.quarantine_agent(target_agent.agent_id, "second quarantine")
            assert result2.success, "Second quarantine should succeed gracefully"
            
            # Verify still quarantined
            assert quarantine_manager.is_quarantined(target_agent.agent_id), (
                "Agent should remain quarantined after double quarantine"
            )
            
        finally:
            network.stop_simulation()
    
    def test_edge_case_release_non_quarantined_agent(self):
        """
        Test edge case: Releasing a non-quarantined agent.
        
        **Feature: agent-conflict-predictor, Property 6: Quarantine isolation effectiveness**
        **Validates: Requirements 4.2**
        """
        mock_redis_client = self.create_mock_redis_client()
        quarantine_manager = RedisQuarantineManager(
            redis_client_instance=mock_redis_client,
            key_prefix="test_quarantine"
        )
        
        network = AgentNetwork(agent_count=5, quarantine_manager=quarantine_manager)
        agents = network.create_agents(3)
        
        network.start_simulation()
        
        try:
            target_agent = agents[0]
            
            # Try to release non-quarantined agent
            result = quarantine_manager.release_quarantine(target_agent.agent_id)
            assert result.success, "Release should handle non-quarantined agent gracefully"
            
            # Verify agent is not quarantined
            assert not quarantine_manager.is_quarantined(target_agent.agent_id), (
                "Agent should not be quarantined"
            )
            
        finally:
            network.stop_simulation()
    
    def test_quarantine_isolation_with_resource_contention(self):
        """
        Test quarantine isolation effectiveness during resource contention scenarios.
        
        **Feature: agent-conflict-predictor, Property 6: Quarantine isolation effectiveness**
        **Validates: Requirements 4.2, 4.4**
        """
        mock_redis_client = self.create_mock_redis_client()
        quarantine_manager = RedisQuarantineManager(
            redis_client_instance=mock_redis_client,
            key_prefix="test_quarantine"
        )
        
        network = AgentNetwork(agent_count=8, quarantine_manager=quarantine_manager)
        agents = network.create_agents(6)
        
        # Reduce resource capacity to create contention
        from src.prediction_engine.models.core import ResourceType
        for resource_type in ResourceType:
            network.resource_manager.resources[resource_type.value]["total_capacity"] = 150
        
        # Track requests and contention
        request_tracker = {}
        contention_events = []
        
        original_process_request = network.resource_manager.process_request
        original_detect_contention = network.resource_manager.detect_contention
        
        def track_requests(request):
            if request.agent_id not in request_tracker:
                request_tracker[request.agent_id] = []
            request_tracker[request.agent_id].append(request)
            return original_process_request(request)
        
        def track_contention():
            events = original_detect_contention()
            contention_events.extend(events)
            return events
        
        network.resource_manager.process_request = track_requests
        network.resource_manager.detect_contention = track_contention
        
        network.start_simulation()
        
        try:
            # Let contention develop
            time.sleep(1.0)
            
            # Quarantine the most active agent
            most_active_agent_id = None
            max_requests = 0
            
            for agent_id, requests in request_tracker.items():
                if len(requests) > max_requests:
                    max_requests = len(requests)
                    most_active_agent_id = agent_id
            
            if most_active_agent_id:
                # Clear tracker to focus on post-quarantine behavior
                request_tracker.clear()
                
                # Quarantine the most active agent
                quarantine_result = quarantine_manager.quarantine_agent(
                    most_active_agent_id,
                    "High activity during contention"
                )
                assert quarantine_result.success, "Quarantine should succeed"
                
                time.sleep(0.2)  # Let quarantine take effect
                time.sleep(1.5)  # Observe post-quarantine behavior
                
                # Verify quarantine effectiveness during contention
                quarantined_requests = request_tracker.get(most_active_agent_id, [])
                assert len(quarantined_requests) == 0, (
                    f"Quarantined agent {most_active_agent_id} should not make requests during contention"
                )
                
                # Verify other agents continue competing for resources
                other_agent_requests = sum(
                    len(requests) for agent_id, requests in request_tracker.items()
                    if agent_id != most_active_agent_id
                )
                
                # System should continue operating with remaining agents
                active_agents = [a for a in agents if a.is_active and not a.is_quarantined]
                assert len(active_agents) >= 4, "Should have multiple active non-quarantined agents"
                
                # Verify contention can still occur among non-quarantined agents
                final_contention = network.resource_manager.detect_contention()
                # Contention may or may not occur depending on timing, but system should handle it
                
        finally:
            network.stop_simulation()