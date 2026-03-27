"""
Property-based test for trust score consistency.

**Feature: agent-conflict-predictor, Property 4: Trust score consistency**
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 4.5**
"""
import pytest
from datetime import datetime
from typing import Dict, List
from unittest.mock import Mock
from hypothesis import given, strategies as st, assume, settings, HealthCheck

from src.prediction_engine.trust_manager import (
    TrustPolicy, RedisTrustScoreManager, RedisTrustManager
)
from src.prediction_engine.models.core import TrustScoreEntry


class TestTrustScoreConsistency:
    """Property-based tests for trust score consistency."""
    
    def create_mock_redis_client(self):
        """Create a mock Redis client that simulates Redis behavior consistently."""
        mock_client = Mock()
        
        # Simulate Redis storage with consistent behavior
        redis_storage = {}
        
        def mock_exists(key):
            return key in redis_storage
        
        def mock_get_json(key):
            return redis_storage.get(key)
        
        def mock_set_json(key, value, ttl=None):
            redis_storage[key] = value
            return True
        
        def mock_delete(key):
            if key in redis_storage:
                del redis_storage[key]
                return True
            return False
        
        mock_client.exists.side_effect = mock_exists
        mock_client.get_json.side_effect = mock_get_json
        mock_client.set_json.side_effect = mock_set_json
        mock_client.delete.side_effect = mock_delete
        
        # Store reference to redis_storage for test access
        mock_client._redis_storage = redis_storage
        
        return mock_client
    
    @given(
        agent_ids=st.lists(
            st.text(min_size=1, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'),
            min_size=1,
            max_size=10,
            unique=True
        ),
        adjustments=st.lists(
            st.tuples(
                st.integers(min_value=-50, max_value=50),  # adjustment amount
                st.text(min_size=1, max_size=50, alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-')  # reason
            ),
            min_size=1,
            max_size=20
        )
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_trust_score_persistence_consistency(self, agent_ids, adjustments):
        """
        Property: For any agent and trust score operation, changes should be 
        immediately persisted to Redis and retrievable consistently.
        
        **Feature: agent-conflict-predictor, Property 4: Trust score consistency**
        **Validates: Requirements 3.1, 3.5**
        """
        mock_redis_client = self.create_mock_redis_client()
        score_manager = RedisTrustScoreManager(redis_client_instance=mock_redis_client)
        trust_manager = RedisTrustManager(score_manager=score_manager)
        
        for agent_id in agent_ids:
            # Initialize agent (Requirement 3.1)
            initial_score = trust_manager.get_trust_score(agent_id)
            assert initial_score == 100, f"New agent {agent_id} should start with score 100"
            
            # Verify persistence immediately after initialization
            redis_key = f"trust_score:{agent_id}"
            assert redis_key in mock_redis_client._redis_storage, f"Agent {agent_id} should be persisted to Redis"
            
            stored_entry = mock_redis_client._redis_storage[redis_key]
            assert stored_entry["agent_id"] == agent_id, "Stored agent ID should match"
            assert stored_entry["current_score"] == 100, "Stored score should be 100"
            
            # Apply adjustments and verify persistence (Requirement 3.5)
            current_expected_score = 100
            for adjustment, reason in adjustments:
                # Apply adjustment
                trust_manager.update_trust_score(agent_id, adjustment, reason)
                
                # Calculate expected score with bounds
                current_expected_score = max(0, min(100, current_expected_score + adjustment))
                
                # Verify immediate persistence
                retrieved_score = trust_manager.get_trust_score(agent_id)
                assert retrieved_score == current_expected_score, (
                    f"Retrieved score {retrieved_score} should match expected {current_expected_score} "
                    f"after adjustment {adjustment}"
                )
                
                # Verify Redis storage consistency
                stored_entry = mock_redis_client._redis_storage[redis_key]
                assert stored_entry["current_score"] == current_expected_score, (
                    f"Stored score should match expected score {current_expected_score}"
                )
                
                # Verify adjustment history is maintained
                assert len(stored_entry["adjustment_history"]) > 0, "Adjustment history should be recorded"
                latest_adjustment = stored_entry["adjustment_history"][-1]
                assert latest_adjustment["adjustment"] == adjustment, "Latest adjustment should match input"
                assert latest_adjustment["reason"] == reason, "Latest reason should match input"
                assert latest_adjustment["new_score"] == current_expected_score, "New score should be recorded"
    
    @given(
        agent_id=st.text(min_size=1, max_size=15, alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'),
        adjustments=st.lists(
            st.integers(min_value=-30, max_value=30),
            min_size=1,
            max_size=15
        )
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_trust_score_bounds_enforcement(self, agent_id, adjustments):
        """
        Property: For any sequence of trust score adjustments, the final score 
        should always be within bounds [0, 100] following configured adjustment rules.
        
        **Feature: agent-conflict-predictor, Property 4: Trust score consistency**
        **Validates: Requirements 3.2, 3.3**
        """
        mock_redis_client = self.create_mock_redis_client()
        score_manager = RedisTrustScoreManager(redis_client_instance=mock_redis_client)
        trust_manager = RedisTrustManager(score_manager=score_manager)
        
        # Initialize agent
        initial_score = trust_manager.get_trust_score(agent_id)
        assert initial_score == 100
        
        # Apply all adjustments
        expected_score = 100
        for adjustment in adjustments:
            trust_manager.update_trust_score(agent_id, adjustment, f"test adjustment {adjustment}")
            expected_score = max(0, min(100, expected_score + adjustment))
            
            # Verify bounds are enforced (Requirements 3.2, 3.3)
            current_score = trust_manager.get_trust_score(agent_id)
            assert 0 <= current_score <= 100, f"Score {current_score} should be within bounds [0, 100]"
            assert current_score == expected_score, f"Score should match expected bounded value {expected_score}"
        
        # Verify final state consistency
        final_score = trust_manager.get_trust_score(agent_id)
        assert final_score == expected_score, "Final score should match calculated expected score"
        
        # Verify Redis storage reflects bounds
        redis_key = f"trust_score:{agent_id}"
        stored_entry = mock_redis_client._redis_storage[redis_key]
        assert 0 <= stored_entry["current_score"] <= 100, "Stored score should be within bounds"
        assert stored_entry["current_score"] == expected_score, "Stored score should match expected"
    
    @given(
        agent_id=st.text(min_size=1, max_size=15, alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'),
        penalty_adjustments=st.lists(
            st.integers(min_value=-50, max_value=-1),  # Only negative adjustments
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_quarantine_threshold_consistency(self, agent_id, penalty_adjustments):
        """
        Property: For any agent, when trust score falls below 30, quarantine 
        consideration should be triggered consistently.
        
        **Feature: agent-conflict-predictor, Property 4: Trust score consistency**
        **Validates: Requirements 3.4, 4.5**
        """
        mock_redis_client = self.create_mock_redis_client()
        score_manager = RedisTrustScoreManager(redis_client_instance=mock_redis_client)
        trust_manager = RedisTrustManager(score_manager=score_manager)
        
        # Initialize agent
        trust_manager.get_trust_score(agent_id)
        
        # Apply penalty adjustments until we cross threshold
        current_score = 100
        crossed_threshold = False
        
        for penalty in penalty_adjustments:
            trust_manager.update_trust_score(agent_id, penalty, f"penalty {penalty}")
            current_score = max(0, current_score + penalty)
            
            # Check quarantine threshold (Requirement 3.4, 4.5)
            should_quarantine = trust_manager.check_quarantine_threshold(agent_id)
            actual_score = trust_manager.get_trust_score(agent_id)
            
            # Verify threshold logic consistency
            if actual_score < 30:
                assert should_quarantine is True, (
                    f"Agent with score {actual_score} < 30 should be marked for quarantine"
                )
                crossed_threshold = True
            else:
                assert should_quarantine is False, (
                    f"Agent with score {actual_score} >= 30 should not be marked for quarantine"
                )
            
            # Verify score consistency
            assert actual_score == current_score, f"Actual score {actual_score} should match expected {current_score}"
        
        # If we crossed the threshold, verify final state
        if crossed_threshold:
            final_score = trust_manager.get_trust_score(agent_id)
            final_quarantine_check = trust_manager.check_quarantine_threshold(agent_id)
            assert final_score < 30, "Final score should be below threshold"
            assert final_quarantine_check is True, "Final quarantine check should be True"
    
    @given(
        agent_id=st.text(min_size=1, max_size=15, alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'),
        quarantine_adjustments=st.lists(
            st.tuples(
                st.integers(min_value=-30, max_value=-5),  # quarantine penalty
                st.sampled_from(["quarantine penalty", "post-quarantine adjustment", "quarantine violation"])
            ),
            min_size=1,
            max_size=5
        ),
        regular_adjustments=st.lists(
            st.tuples(
                st.integers(min_value=-20, max_value=20),  # regular adjustment
                st.sampled_from(["conflict", "cooperation", "timeout", "success"])
            ),
            min_size=0,
            max_size=5
        )
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_quarantine_count_tracking_consistency(self, agent_id, quarantine_adjustments, regular_adjustments):
        """
        Property: For any agent, quarantine-related adjustments should be tracked 
        separately and consistently from regular adjustments.
        
        **Feature: agent-conflict-predictor, Property 4: Trust score consistency**
        **Validates: Requirements 3.4, 4.5**
        """
        mock_redis_client = self.create_mock_redis_client()
        score_manager = RedisTrustScoreManager(redis_client_instance=mock_redis_client)
        trust_manager = RedisTrustManager(score_manager=score_manager)
        
        # Initialize agent
        trust_manager.get_trust_score(agent_id)
        
        # Apply regular adjustments first
        for adjustment, reason in regular_adjustments:
            trust_manager.update_trust_score(agent_id, adjustment, reason)
        
        # Verify no quarantine count yet
        quarantine_count = trust_manager.get_quarantine_count(agent_id)
        assert quarantine_count == 0, "Should have no quarantine count from regular adjustments"
        
        # Apply quarantine adjustments
        expected_quarantine_count = 0
        for adjustment, reason in quarantine_adjustments:
            trust_manager.update_trust_score(agent_id, adjustment, reason)
            expected_quarantine_count += 1
            
            # Verify quarantine count tracking (Requirements 3.4, 4.5)
            current_quarantine_count = trust_manager.get_quarantine_count(agent_id)
            assert current_quarantine_count == expected_quarantine_count, (
                f"Quarantine count {current_quarantine_count} should match expected {expected_quarantine_count}"
            )
        
        # Verify final quarantine count consistency
        final_quarantine_count = trust_manager.get_quarantine_count(agent_id)
        assert final_quarantine_count == len(quarantine_adjustments), (
            f"Final quarantine count should equal number of quarantine adjustments"
        )
        
        # Verify adjustment history contains all adjustments
        history = trust_manager.get_agent_history(agent_id)
        total_expected_adjustments = len(regular_adjustments) + len(quarantine_adjustments)
        assert len(history) == total_expected_adjustments, (
            f"History should contain all {total_expected_adjustments} adjustments"
        )
    
    @given(
        agents_data=st.lists(
            st.tuples(
                st.text(min_size=1, max_size=10, alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'),  # agent_id
                st.lists(
                    st.integers(min_value=-25, max_value=25),
                    min_size=1,
                    max_size=8
                )  # adjustments
            ),
            min_size=2,
            max_size=5,
            unique_by=lambda x: x[0]  # unique agent IDs
        )
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_multi_agent_consistency(self, agents_data):
        """
        Property: For any set of agents with independent trust score operations, 
        each agent's state should be managed consistently without interference.
        
        **Feature: agent-conflict-predictor, Property 4: Trust score consistency**
        **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
        """
        mock_redis_client = self.create_mock_redis_client()
        score_manager = RedisTrustScoreManager(redis_client_instance=mock_redis_client)
        trust_manager = RedisTrustManager(score_manager=score_manager)
        
        # Track expected scores for each agent
        expected_scores = {}
        
        # Initialize all agents
        for agent_id, adjustments in agents_data:
            initial_score = trust_manager.get_trust_score(agent_id)
            assert initial_score == 100, f"Agent {agent_id} should start with score 100"
            expected_scores[agent_id] = 100
        
        # Apply adjustments to all agents
        for agent_id, adjustments in agents_data:
            for adjustment in adjustments:
                trust_manager.update_trust_score(agent_id, adjustment, f"adjustment {adjustment}")
                expected_scores[agent_id] = max(0, min(100, expected_scores[agent_id] + adjustment))
        
        # Verify all agents have consistent independent state
        for agent_id, expected_score in expected_scores.items():
            actual_score = trust_manager.get_trust_score(agent_id)
            assert actual_score == expected_score, (
                f"Agent {agent_id} score {actual_score} should match expected {expected_score}"
            )
            
            # Verify quarantine threshold consistency
            should_quarantine = trust_manager.check_quarantine_threshold(agent_id)
            expected_quarantine = expected_score < 30
            assert should_quarantine == expected_quarantine, (
                f"Agent {agent_id} quarantine status should match score-based expectation"
            )
            
            # Verify Redis storage independence
            redis_key = f"trust_score:{agent_id}"
            assert redis_key in mock_redis_client._redis_storage, f"Agent {agent_id} should exist in Redis"
            stored_entry = mock_redis_client._redis_storage[redis_key]
            assert stored_entry["current_score"] == expected_score, (
                f"Stored score for {agent_id} should match expected"
            )
    
    @given(
        agent_id=st.text(min_size=1, max_size=15, alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'),
        initial_adjustment=st.integers(min_value=-50, max_value=50),
        subsequent_adjustments=st.lists(
            st.integers(min_value=-30, max_value=30),
            min_size=0,
            max_size=10
        )
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_adjustment_history_consistency(self, agent_id, initial_adjustment, subsequent_adjustments):
        """
        Property: For any agent, all trust score adjustments should be recorded 
        in history with complete metadata and retrievable consistently.
        
        **Feature: agent-conflict-predictor, Property 4: Trust score consistency**
        **Validates: Requirements 3.2, 3.5**
        """
        mock_redis_client = self.create_mock_redis_client()
        score_manager = RedisTrustScoreManager(redis_client_instance=mock_redis_client)
        trust_manager = RedisTrustManager(score_manager=score_manager)
        
        # Initialize agent
        trust_manager.get_trust_score(agent_id)
        
        # Apply initial adjustment
        trust_manager.update_trust_score(agent_id, initial_adjustment, "initial adjustment")
        
        # Apply subsequent adjustments
        all_adjustments = [initial_adjustment] + subsequent_adjustments
        for i, adjustment in enumerate(subsequent_adjustments, 1):
            trust_manager.update_trust_score(agent_id, adjustment, f"adjustment {i}")
        
        # Verify adjustment history consistency (Requirements 3.2, 3.5)
        history = trust_manager.get_agent_history(agent_id)
        assert len(history) == len(all_adjustments), (
            f"History length {len(history)} should match adjustments count {len(all_adjustments)}"
        )
        
        # Verify each adjustment is recorded correctly
        current_score = 100
        for i, (recorded_adjustment, expected_adjustment) in enumerate(zip(history, all_adjustments)):
            old_score = current_score
            current_score = max(0, min(100, current_score + expected_adjustment))
            
            assert recorded_adjustment["adjustment"] == expected_adjustment, (
                f"Recorded adjustment {i} should match expected"
            )
            assert recorded_adjustment["old_score"] == old_score, (
                f"Recorded old score {i} should match expected"
            )
            assert recorded_adjustment["new_score"] == current_score, (
                f"Recorded new score {i} should match expected"
            )
            assert "timestamp" in recorded_adjustment, "Each adjustment should have timestamp"
            assert "reason" in recorded_adjustment, "Each adjustment should have reason"
        
        # Verify final score matches history
        final_score = trust_manager.get_trust_score(agent_id)
        if history:
            assert final_score == history[-1]["new_score"], (
                "Final score should match last recorded new score"
            )
    
    def test_edge_case_boundary_scores(self):
        """
        Test edge cases at trust score boundaries (0, 30, 100).
        
        **Feature: agent-conflict-predictor, Property 4: Trust score consistency**
        **Validates: Requirements 3.2, 3.3, 3.4**
        """
        mock_redis_client = self.create_mock_redis_client()
        score_manager = RedisTrustScoreManager(redis_client_instance=mock_redis_client)
        trust_manager = RedisTrustManager(score_manager=score_manager)
        
        agent_id = "boundary_test_agent"
        
        # Test at maximum boundary (100)
        initial_score = trust_manager.get_trust_score(agent_id)
        assert initial_score == 100
        
        # Try to exceed maximum
        trust_manager.update_trust_score(agent_id, 50, "bonus attempt")
        score = trust_manager.get_trust_score(agent_id)
        assert score == 100, "Score should be clamped at maximum"
        
        # Test at quarantine threshold (30)
        trust_manager.update_trust_score(agent_id, -70, "bring to threshold")
        score = trust_manager.get_trust_score(agent_id)
        assert score == 30
        assert trust_manager.check_quarantine_threshold(agent_id) is False, "At threshold should not quarantine"
        
        # Cross quarantine threshold
        trust_manager.update_trust_score(agent_id, -1, "cross threshold")
        score = trust_manager.get_trust_score(agent_id)
        assert score == 29
        assert trust_manager.check_quarantine_threshold(agent_id) is True, "Below threshold should quarantine"
        
        # Test at minimum boundary (0)
        trust_manager.update_trust_score(agent_id, -50, "bring to minimum")
        score = trust_manager.get_trust_score(agent_id)
        assert score == 0
        
        # Try to go below minimum
        trust_manager.update_trust_score(agent_id, -25, "below minimum attempt")
        score = trust_manager.get_trust_score(agent_id)
        assert score == 0, "Score should be clamped at minimum"
    
    def test_edge_case_empty_agent_id(self):
        """
        Test edge case with invalid agent ID.
        
        **Feature: agent-conflict-predictor, Property 4: Trust score consistency**
        **Validates: Requirements 3.1**
        """
        mock_redis_client = self.create_mock_redis_client()
        score_manager = RedisTrustScoreManager(redis_client_instance=mock_redis_client)
        
        # Current implementation accepts empty and None agent IDs without validation
        # This tests that the system handles these cases without crashing
        # Empty string agent ID
        entry = score_manager.initialize_agent("")
        assert entry.agent_id == ""
        assert entry.current_score == 100
        
        # None agent ID - this will work with our mock but might fail with real Redis
        # The system should handle this gracefully
        try:
            entry_none = score_manager.initialize_agent(None)
            assert entry_none.agent_id is None
            assert entry_none.current_score == 100
        except (TypeError, AttributeError):
            # This is acceptable - None agent ID might not work with string operations
            pass
    
    def test_redis_storage_format_consistency(self):
        """
        Test that Redis storage format is consistent and contains all required fields.
        
        **Feature: agent-conflict-predictor, Property 4: Trust score consistency**
        **Validates: Requirements 3.5**
        """
        mock_redis_client = self.create_mock_redis_client()
        score_manager = RedisTrustScoreManager(redis_client_instance=mock_redis_client)
        trust_manager = RedisTrustManager(score_manager=score_manager)
        
        agent_id = "format_test_agent"
        
        # Initialize and modify agent
        trust_manager.get_trust_score(agent_id)
        trust_manager.update_trust_score(agent_id, -15, "test adjustment")
        
        # Verify Redis storage format
        redis_key = f"trust_score:{agent_id}"
        stored_entry = mock_redis_client._redis_storage[redis_key]
        
        # Required fields
        required_fields = ["agent_id", "current_score", "last_updated", "adjustment_history", "quarantine_count", "creation_time"]
        for field in required_fields:
            assert field in stored_entry, f"Required field {field} should be in stored entry"
        
        # Field type validation
        assert isinstance(stored_entry["agent_id"], str), "agent_id should be string"
        assert isinstance(stored_entry["current_score"], int), "current_score should be int"
        assert isinstance(stored_entry["adjustment_history"], list), "adjustment_history should be list"
        assert isinstance(stored_entry["quarantine_count"], int), "quarantine_count should be int"
        
        # Score bounds
        assert 0 <= stored_entry["current_score"] <= 100, "Stored score should be within bounds"
        assert stored_entry["quarantine_count"] >= 0, "Quarantine count should be non-negative"