"""
Property-based tests for Trust Policy application and Analytics calculation.

**Feature: observability-trust-layer, Property 10: Trust policy application**
**Validates: Requirements 5.1, 5.5**
"""
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime, timedelta
import math
from typing import Dict, List, Tuple
from dataclasses import asdict

from unittest.mock import Mock, MagicMock
from src.prediction_engine.trust_manager import (
    RedisTrustManager, RedisTrustScoreManager, TrustPolicy, TrustScoreEntry
)


class TestTrustPolicyApplication:
    """Property-based tests for trust policy application."""
    
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
        agent_interactions=st.lists(
            st.tuples(
                st.text(min_size=1, max_size=15, alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'),  # agent_id
                st.sampled_from(['conflict', 'cooperation', 'quarantine', 'timeout', 'success']),  # interaction_type
                st.integers(min_value=1, max_value=5)  # severity/frequency
            ),
            min_size=1,
            max_size=20,
            unique_by=lambda x: x[0]  # unique agent IDs
        )
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_trust_policy_application_configurable_adjustments(self, agent_interactions):
        """
        Property 10: Trust policy application - configurable policies based on conflict severity and frequency.
        
        For any agent interaction, trust adjustments should be calculated using the current 
        policy configuration without affecting historical data.
        
        **Feature: observability-trust-layer, Property 10: Trust policy application**
        **Validates: Requirements 5.1, 5.5**
        """
        mock_redis_client = self.create_mock_redis_client()
        score_manager = RedisTrustScoreManager(redis_client_instance=mock_redis_client)
        trust_manager = RedisTrustManager(score_manager=score_manager)
        
        # Define policy-based adjustments (Requirement 5.1)
        policy_adjustments = {
            'conflict': lambda severity: -10 * severity,  # More severe conflicts = bigger penalty
            'cooperation': lambda frequency: 5 * min(frequency, 3),  # Cooperation bonus, capped
            'quarantine': lambda severity: -20 * severity,  # Quarantine penalty
            'timeout': lambda frequency: -5 * frequency,  # Timeout penalty
            'success': lambda frequency: 1 * frequency  # Success bonus
        }
        
        # Track expected scores and historical data for each agent
        expected_scores = {}
        historical_data = {}
        
        for agent_id, interaction_type, severity_frequency in agent_interactions:
            # Initialize agent if not exists
            if agent_id not in expected_scores:
                initial_score = trust_manager.get_trust_score(agent_id)
                expected_scores[agent_id] = initial_score
                historical_data[agent_id] = []
            
            # Calculate policy-based adjustment (Requirement 5.1)
            adjustment = policy_adjustments[interaction_type](severity_frequency)
            reason = f"{interaction_type} (severity/frequency: {severity_frequency})"
            
            # Store historical state before adjustment (Requirement 5.5)
            pre_adjustment_history = trust_manager.get_agent_history(agent_id).copy()
            
            # Apply adjustment using current policy
            trust_manager.update_trust_score(agent_id, adjustment, reason)
            
            # Calculate expected score with bounds
            old_score = expected_scores[agent_id]
            expected_scores[agent_id] = max(0, min(100, old_score + adjustment))
            
            # Verify policy application (Requirement 5.1)
            actual_score = trust_manager.get_trust_score(agent_id)
            assert actual_score == expected_scores[agent_id], (
                f"Agent {agent_id}: Policy-based adjustment should result in expected score. "
                f"Expected: {expected_scores[agent_id]}, Actual: {actual_score}, "
                f"Adjustment: {adjustment} for {interaction_type}"
            )
            
            # Verify historical data preservation (Requirement 5.5)
            post_adjustment_history = trust_manager.get_agent_history(agent_id)
            
            # Historical data should be preserved - only new entry added
            assert len(post_adjustment_history) == len(pre_adjustment_history) + 1, (
                f"Agent {agent_id}: Historical data should be preserved with one new entry added"
            )
            
            # Previous historical entries should be unchanged
            for i, (old_entry, new_entry) in enumerate(zip(pre_adjustment_history, post_adjustment_history[:-1])):
                assert old_entry == new_entry, (
                    f"Agent {agent_id}: Historical entry {i} should be unchanged after policy application"
                )
            
            # New entry should reflect the policy-based adjustment
            latest_entry = post_adjustment_history[-1]
            assert latest_entry["adjustment"] == adjustment, (
                f"Agent {agent_id}: Latest adjustment should match policy calculation"
            )
            assert latest_entry["old_score"] == old_score, (
                f"Agent {agent_id}: Old score should be preserved in history"
            )
            assert latest_entry["new_score"] == expected_scores[agent_id], (
                f"Agent {agent_id}: New score should match policy-adjusted score"
            )
            assert latest_entry["reason"] == reason, (
                f"Agent {agent_id}: Reason should include interaction type and severity/frequency"
            )
            
            # Store for cross-verification
            historical_data[agent_id].append({
                'interaction_type': interaction_type,
                'severity_frequency': severity_frequency,
                'adjustment': adjustment,
                'old_score': old_score,
                'new_score': expected_scores[agent_id]
            })
        
        # Final verification: All agents should have consistent policy application
        for agent_id in expected_scores:
            final_score = trust_manager.get_trust_score(agent_id)
            assert final_score == expected_scores[agent_id], (
                f"Agent {agent_id}: Final score should match cumulative policy applications"
            )
            
            # Verify complete history integrity
            complete_history = trust_manager.get_agent_history(agent_id)
            assert len(complete_history) == len(historical_data[agent_id]), (
                f"Agent {agent_id}: Complete history should match number of interactions"
            )
    
    @given(
        agent_id=st.text(min_size=1, max_size=15, alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'),
        initial_interactions=st.lists(
            st.tuples(
                st.sampled_from(['conflict', 'cooperation', 'timeout']),
                st.integers(min_value=1, max_value=3)
            ),
            min_size=1,
            max_size=5
        ),
        policy_change_interactions=st.lists(
            st.tuples(
                st.sampled_from(['conflict', 'cooperation', 'timeout']),
                st.integers(min_value=1, max_value=3)
            ),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_trust_policy_change_historical_preservation(self, agent_id, initial_interactions, policy_change_interactions):
        """
        Property 10: Trust policy application - policy changes don't affect historical data.
        
        When trust policies change, the system should apply new rules to future interactions 
        without affecting historical data.
        
        **Feature: observability-trust-layer, Property 10: Trust policy application**
        **Validates: Requirements 5.5**
        """
        mock_redis_client = self.create_mock_redis_client()
        score_manager = RedisTrustScoreManager(redis_client_instance=mock_redis_client)
        trust_manager = RedisTrustManager(score_manager=score_manager)
        
        # Original policy adjustments
        original_policy = {
            'conflict': lambda severity: -10 * severity,
            'cooperation': lambda frequency: 5 * frequency,
            'timeout': lambda frequency: -5 * frequency
        }
        
        # Initialize agent
        trust_manager.get_trust_score(agent_id)
        
        # Apply initial interactions with original policy
        for interaction_type, severity_frequency in initial_interactions:
            adjustment = original_policy[interaction_type](severity_frequency)
            reason = f"original_policy_{interaction_type}_s{severity_frequency}"
            trust_manager.update_trust_score(agent_id, adjustment, reason)
        
        # Capture historical data after initial interactions
        historical_snapshot = trust_manager.get_agent_history(agent_id)
        historical_snapshot_copy = [entry.copy() for entry in historical_snapshot]
        
        # Simulate policy change by creating new policy adjustments
        new_policy = {
            'conflict': lambda severity: -15 * severity,  # Increased penalty
            'cooperation': lambda frequency: 8 * frequency,  # Increased bonus
            'timeout': lambda frequency: -3 * frequency  # Reduced penalty
        }
        
        # Apply new interactions with changed policy
        for interaction_type, severity_frequency in policy_change_interactions:
            # Use new policy for calculation
            adjustment = new_policy[interaction_type](severity_frequency)
            reason = f"new_policy_{interaction_type}_s{severity_frequency}"
            trust_manager.update_trust_score(agent_id, adjustment, reason)
        
        # Verify historical data preservation (Requirement 5.5)
        current_history = trust_manager.get_agent_history(agent_id)
        
        # Historical entries should be unchanged
        assert len(current_history) >= len(historical_snapshot_copy), (
            "History should only grow, never shrink"
        )
        
        # Original historical entries should be exactly preserved
        for i, (original_entry, current_entry) in enumerate(zip(historical_snapshot_copy, current_history[:len(historical_snapshot_copy)])):
            assert original_entry == current_entry, (
                f"Historical entry {i} should be unchanged after policy change. "
                f"Original: {original_entry}, Current: {current_entry}"
            )
        
        # New entries should reflect new policy
        new_entries = current_history[len(historical_snapshot_copy):]
        assert len(new_entries) == len(policy_change_interactions), (
            "Should have one new entry per new interaction"
        )
        
        for entry, (interaction_type, severity_frequency) in zip(new_entries, policy_change_interactions):
            expected_adjustment = new_policy[interaction_type](severity_frequency)
            assert entry["adjustment"] == expected_adjustment, (
                f"New entry should use new policy adjustment. "
                f"Expected: {expected_adjustment}, Actual: {entry['adjustment']}"
            )
            assert f"new_policy_{interaction_type}" in entry["reason"], (
                "New entry should indicate new policy usage"
            )
        
        # Verify score calculation integrity
        # Recalculate expected final score
        expected_final_score = 100  # Initial score
        
        # Apply original interactions
        for interaction_type, severity_frequency in initial_interactions:
            adjustment = original_policy[interaction_type](severity_frequency)
            expected_final_score = max(0, min(100, expected_final_score + adjustment))
        
        # Apply new policy interactions
        for interaction_type, severity_frequency in policy_change_interactions:
            adjustment = new_policy[interaction_type](severity_frequency)
            expected_final_score = max(0, min(100, expected_final_score + adjustment))
        
        actual_final_score = trust_manager.get_trust_score(agent_id)
        assert actual_final_score == expected_final_score, (
            f"Final score should reflect both original and new policy applications. "
            f"Expected: {expected_final_score}, Actual: {actual_final_score}"
        )
    
    @given(
        current_score=st.integers(min_value=-50, max_value=150),
        adjustment=st.integers(min_value=-200, max_value=200)
    )
    @settings(max_examples=100)
    def test_property_trust_policy_bounds_enforcement(self, current_score, adjustment):
        """
        Property 10: Trust policy application - bounds enforcement.
        
        For any trust score and adjustment, the policy should enforce bounds [0, 100].
        
        **Feature: observability-trust-layer, Property 10: Trust policy application**
        **Validates: Requirements 5.1**
        """
        # Test the core policy adjustment function
        new_score = TrustPolicy.apply_adjustment(current_score, adjustment)
        
        # Verify bounds enforcement (Requirement 5.1)
        assert TrustPolicy.MIN_SCORE <= new_score <= TrustPolicy.MAX_SCORE, (
            f"Score {new_score} should be within bounds [{TrustPolicy.MIN_SCORE}, {TrustPolicy.MAX_SCORE}]"
        )
        
        # Verify adjustment direction when not at bounds
        if TrustPolicy.MIN_SCORE < current_score < TrustPolicy.MAX_SCORE:
            if adjustment > 0:
                assert new_score >= current_score, "Positive adjustment should increase or maintain score"
            elif adjustment < 0:
                assert new_score <= current_score, "Negative adjustment should decrease or maintain score"
            else:  # adjustment == 0
                assert new_score == current_score, "Zero adjustment should maintain score"
        
        # Verify clamping behavior
        expected_unclamped = current_score + adjustment
        if expected_unclamped > TrustPolicy.MAX_SCORE:
            assert new_score == TrustPolicy.MAX_SCORE, "Should clamp to maximum"
        elif expected_unclamped < TrustPolicy.MIN_SCORE:
            assert new_score == TrustPolicy.MIN_SCORE, "Should clamp to minimum"
        else:
            assert new_score == expected_unclamped, "Should apply adjustment when within bounds"
    
    def test_edge_case_policy_constants_consistency(self):
        """
        Test that policy constants are consistent and reasonable.
        
        **Feature: observability-trust-layer, Property 10: Trust policy application**
        **Validates: Requirements 5.1**
        """
        # Verify policy constants are reasonable
        assert TrustPolicy.MIN_SCORE == 0, "Minimum score should be 0"
        assert TrustPolicy.MAX_SCORE == 100, "Maximum score should be 100"
        assert TrustPolicy.MIN_SCORE < TrustPolicy.MAX_SCORE, "Min should be less than max"
        assert TrustPolicy.MIN_SCORE <= TrustPolicy.INITIAL_SCORE <= TrustPolicy.MAX_SCORE, (
            "Initial score should be within bounds"
        )
        assert TrustPolicy.QUARANTINE_THRESHOLD >= TrustPolicy.MIN_SCORE, (
            "Quarantine threshold should be above minimum"
        )
        assert TrustPolicy.QUARANTINE_THRESHOLD < TrustPolicy.INITIAL_SCORE, (
            "Quarantine threshold should be below initial score"
        )
        
        # Verify adjustment constants are reasonable
        assert TrustPolicy.CONFLICT_PENALTY < 0, "Conflict penalty should be negative"
        assert TrustPolicy.COOPERATION_BONUS > 0, "Cooperation bonus should be positive"
        assert TrustPolicy.QUARANTINE_PENALTY < 0, "Quarantine penalty should be negative"
        assert TrustPolicy.TIMEOUT_PENALTY < 0, "Timeout penalty should be negative"
        assert TrustPolicy.SUCCESSFUL_REQUEST_BONUS > 0, "Success bonus should be positive"
        
        # Verify penalty/bonus magnitudes are reasonable
        assert abs(TrustPolicy.QUARANTINE_PENALTY) > abs(TrustPolicy.CONFLICT_PENALTY), (
            "Quarantine penalty should be more severe than conflict penalty"
        )
        assert TrustPolicy.COOPERATION_BONUS > TrustPolicy.SUCCESSFUL_REQUEST_BONUS, (
            "Cooperation bonus should be larger than success bonus"
        )


class TestTrustAnalyticsCalculation:
    """Property-based tests for trust analytics calculation accuracy."""
    
    @given(
        agent_interactions=st.lists(
            st.tuples(
                st.text(min_size=1, max_size=15, alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'),  # agent_id
                st.sampled_from(['conflict', 'cooperation', 'quarantine', 'timeout', 'success']),  # interaction_type
                st.integers(min_value=1, max_value=5)  # severity/frequency
            ),
            min_size=5,
            max_size=50
        )
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_analytics_calculation_accuracy_cooperation_and_conflict_metrics(self, agent_interactions):
        """
        Property 11: Analytics calculation accuracy.
        
        For any set of agent interactions, cooperation metrics and conflict participation rates 
        should be calculated consistently based on the interaction data.
        
        **Feature: observability-trust-layer, Property 11: Analytics calculation accuracy**
        **Validates: Requirements 5.3, 5.4**
        """
        mock_redis_client = self.create_mock_redis_client()
        score_manager = RedisTrustScoreManager(redis_client_instance=mock_redis_client)
        trust_manager = RedisTrustManager(score_manager=score_manager)
        
        # Track expected metrics per agent
        agent_metrics = {}
        
        for agent_id, interaction_type, severity_frequency in agent_interactions:
            if agent_id not in agent_metrics:
                agent_metrics[agent_id] = {
                    'total_interactions': 0,
                    'cooperation_count': 0,
                    'conflict_count': 0,
                    'quarantine_count': 0,
                    'timeout_count': 0,
                    'success_count': 0,
                    'total_severity': 0
                }
            
            # Initialize agent if needed
            trust_manager.get_trust_score(agent_id)
            
            # Apply interaction and track metrics
            adjustment_map = {
                'conflict': -10 * severity_frequency,
                'cooperation': 5 * severity_frequency,
                'quarantine': -20 * severity_frequency,
                'timeout': -5 * severity_frequency,
                'success': 1 * severity_frequency
            }
            
            adjustment = adjustment_map[interaction_type]
            reason = f"{interaction_type}_severity_{severity_frequency}"
            trust_manager.update_trust_score(agent_id, adjustment, reason)
            
            # Update expected metrics
            metrics = agent_metrics[agent_id]
            metrics['total_interactions'] += 1
            metrics[f'{interaction_type}_count'] += 1
            metrics['total_severity'] += severity_frequency
        
        # Verify analytics calculations for each agent (Requirements 5.3, 5.4)
        for agent_id, expected_metrics in agent_metrics.items():
            analytics = trust_manager.get_trust_score_analytics(agent_id)
            history = trust_manager.get_agent_history(agent_id)
            
            # Calculate expected cooperation metrics (Requirement 5.3)
            total_interactions = expected_metrics['total_interactions']
            cooperation_rate = expected_metrics['cooperation_count'] / total_interactions if total_interactions > 0 else 0
            conflict_participation_rate = expected_metrics['conflict_count'] / total_interactions if total_interactions > 0 else 0
            
            # Verify basic analytics exist (Requirement 5.4)
            assert "trend" in analytics, f"Agent {agent_id}: Analytics should include trend calculation"
            assert "volatility" in analytics, f"Agent {agent_id}: Analytics should include volatility calculation"
            assert "average_adjustment" in analytics, f"Agent {agent_id}: Analytics should include average adjustment"
            
            # Verify trend calculation accuracy (Requirement 5.4)
            scores = [item["new_score"] for item in history]
            if len(scores) >= 2:
                # Trend should be consistent with score progression
                if scores[-1] > scores[0]:
                    assert analytics["trend"] >= 0, f"Agent {agent_id}: Positive score progression should have non-negative trend"
                elif scores[-1] < scores[0]:
                    assert analytics["trend"] <= 0, f"Agent {agent_id}: Negative score progression should have non-positive trend"
            
            # Verify volatility is non-negative (Requirement 5.4)
            assert analytics["volatility"] >= 0, f"Agent {agent_id}: Volatility should be non-negative"
            
            # Verify average adjustment calculation (Requirement 5.4)
            adjustments = [item["adjustment"] for item in history]
            expected_avg = sum(adjustments) / len(adjustments) if adjustments else 0
            assert abs(analytics["average_adjustment"] - expected_avg) < 1e-9, (
                f"Agent {agent_id}: Average adjustment calculation should be accurate"
            )
            
            # Verify cooperation metrics can be derived from history (Requirement 5.3)
            cooperation_interactions = [item for item in history if 'cooperation' in item["reason"]]
            conflict_interactions = [item for item in history if 'conflict' in item["reason"]]
            
            actual_cooperation_count = len(cooperation_interactions)
            actual_conflict_count = len(conflict_interactions)
            
            assert actual_cooperation_count == expected_metrics['cooperation_count'], (
                f"Agent {agent_id}: Cooperation count should match expected value"
            )
            assert actual_conflict_count == expected_metrics['conflict_count'], (
                f"Agent {agent_id}: Conflict count should match expected value"
            )
            
            # Verify conflict participation rate calculation (Requirement 5.3)
            actual_conflict_rate = actual_conflict_count / len(history) if history else 0
            assert abs(actual_conflict_rate - conflict_participation_rate) < 1e-9, (
                f"Agent {agent_id}: Conflict participation rate should be calculated correctly"
            )
            
            # Verify cooperation rate calculation (Requirement 5.3)
            actual_cooperation_rate = actual_cooperation_count / len(history) if history else 0
            assert abs(actual_cooperation_rate - cooperation_rate) < 1e-9, (
                f"Agent {agent_id}: Cooperation rate should be calculated correctly"
            )
    
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
        adjustments=st.lists(st.integers(min_value=-10, max_value=10), min_size=2, max_size=20)
    )
    @settings(max_examples=100)
    def test_property_analytics_calculation_accuracy_trend_and_volatility(self, adjustments):
        """
        Property 11: Analytics calculation accuracy - trend and volatility calculations.
        
        Verify trend and volatility calculations against known mathematical properties.
        
        **Feature: observability-trust-layer, Property 11: Analytics calculation accuracy**
        **Validates: Requirements 5.4**
        """
        # Setup mock manager with history
        mock_score_manager = Mock(spec=RedisTrustScoreManager)
        trust_manager = RedisTrustManager(score_manager=mock_score_manager)
        
        # Construct history
        history = []
        current = 100
        scores = []
        
        for adj in adjustments:
            new_score = max(0, min(100, current + adj))
            history.append({
                "timestamp": datetime.now().isoformat(),
                "adjustment": adj,
                "old_score": current,
                "new_score": new_score,
                "reason": "test"
            })
            scores.append(new_score)
            current = new_score
            
        mock_score_manager.get_score_entry.return_value = TrustScoreEntry(
            agent_id="test",
            current_score=current,
            last_updated=datetime.now(),
            adjustment_history=history,
            quarantine_count=0,
            creation_time=datetime.now()
        )
        
        analytics = trust_manager.get_trust_score_analytics("test")
        
        # Verify Volatility (Std Dev) >= 0 (Requirement 5.4)
        assert analytics["volatility"] >= 0, "Volatility should be non-negative"
        
        # Verify Trend calculation properties (Requirement 5.4)
        # If adjustments are all positive, trend should be positive (or zero if capped)
        # Note: We calculate trend on SCORES, not adjustments
        if all(s2 >= s1 for s1, s2 in zip(scores, scores[1:])) and scores[-1] > scores[0]:
            assert analytics["trend"] >= 0, "Monotonically increasing scores should have non-negative trend"
            
        if all(s2 <= s1 for s1, s2 in zip(scores, scores[1:])) and scores[-1] < scores[0]:
            assert analytics["trend"] <= 0, "Monotonically decreasing scores should have non-positive trend"
            
        # Verify Average Adjustment matches simple calculation (Requirement 5.4)
        avg_calc = sum(adjustments) / len(adjustments)
        assert abs(analytics["average_adjustment"] - avg_calc) < 1e-9, (
            "Average adjustment should match mathematical calculation"
        )
        
        # Verify trend calculation for constant scores (Requirement 5.4)
        if all(score == scores[0] for score in scores):
            assert abs(analytics["trend"]) < 1e-9, "Constant scores should have zero trend"
        
        # Verify volatility calculation for constant scores (Requirement 5.4)
        if len(set(scores)) == 1:  # All scores are the same
            assert abs(analytics["volatility"]) < 1e-9, "Constant scores should have zero volatility"

