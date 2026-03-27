"""
Property-based test for CLI real-time updates.

**Feature: agent-conflict-predictor, Property 8: Real-time CLI updates**
**Validates: Requirements 5.3, 5.4, 5.5**
"""
import pytest
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, assume, settings, HealthCheck

from src.prediction_engine.cli_dashboard import CLIDashboard, DashboardMetrics
from src.prediction_engine.models.core import ConflictAnalysis, InterventionAction


class TestCLIRealTimeUpdates:
    """Property-based tests for CLI real-time updates."""
    
    def create_mock_system_components(self):
        """Create mock system components for testing CLI updates."""
        # Mock conflict predictor system
        mock_system = Mock()
        mock_system.get_system_status.return_value = {
            "system_running": True,
            "total_agents": 8,
            "active_agents": 6,
            "quarantined_agents": 2
        }
        
        # Mock agent network
        mock_agent_network = Mock()
        mock_agent_network.get_active_agents.return_value = [
            Mock(agent_id="agent_001"),
            Mock(agent_id="agent_002"),
            Mock(agent_id="agent_003")
        ]
        mock_agent_network.get_all_intentions.return_value = []
        mock_agent_network.resource_manager = Mock()
        
        # Mock resource manager
        mock_resource_manager = Mock()
        mock_resource_status = Mock()
        mock_resource_status.current_usage = 150
        mock_resource_status.total_capacity = 200
        mock_resource_manager.get_resource_status.return_value = mock_resource_status
        
        # Mock trust manager
        mock_trust_manager = Mock()
        mock_trust_manager.get_trust_score.return_value = 85
        
        # Mock intervention engine
        mock_intervention_engine = Mock()
        mock_intervention_engine.get_intervention_history.return_value = []
        
        mock_system.agent_network = mock_agent_network
        mock_system.trust_manager = mock_trust_manager
        mock_system.intervention_engine = mock_intervention_engine
        
        return mock_system
    
    def create_test_dashboard_metrics(self, **overrides):
        """Create test dashboard metrics with optional overrides."""
        defaults = {
            'timestamp': datetime.now(),
            'total_agents': 8,
            'active_agents': 6,
            'quarantined_agents': 2,
            'system_running': True,
            'recent_conflicts': [],
            'recent_interventions': [],
            'resource_utilization': {'cpu': 0.75, 'memory': 0.60},
            'trust_scores': {'agent_001': 85, 'agent_002': 92},
            'current_risk_score': 0.65,
            'gemini_api_status': True
        }
        defaults.update(overrides)
        return DashboardMetrics(**defaults)
    
    @given(
        risk_scores=st.lists(
            st.floats(min_value=0.0, max_value=1.0),
            min_size=1,
            max_size=3
        ),
        affected_agents=st.lists(
            st.lists(
                st.text(min_size=1, max_size=8, alphabet='abcdefghijklmnopqrstuvwxyz0123456789_'),
                min_size=1,
                max_size=3,
                unique=True
            ),
            min_size=1,
            max_size=3
        )
    )
    @settings(max_examples=10, deadline=3000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_conflict_predictions_display_automatically(self, risk_scores, affected_agents):
        """
        Property: For any conflict analysis with risk score and affected agents, 
        the CLI should display updates automatically without user input.
        
        **Feature: agent-conflict-predictor, Property 8: Real-time CLI updates**
        **Validates: Requirements 5.3, 5.4**
        """
        assume(len(risk_scores) == len(affected_agents))
        
        dashboard = CLIDashboard()
        
        # Create test conflict analyses
        conflict_analyses = []
        for i, (risk_score, agents) in enumerate(zip(risk_scores, affected_agents)):
            analysis = ConflictAnalysis(
                risk_score=risk_score,
                confidence_level=0.9,
                affected_agents=agents,
                predicted_failure_mode=f"Test failure mode {i}",
                nash_equilibrium=None,
                timestamp=datetime.now()
            )
            conflict_analyses.append(analysis)
        
        # Test metrics collection with conflict data
        test_metrics = self.create_test_dashboard_metrics(
            recent_conflicts=conflict_analyses,
            current_risk_score=risk_scores[0] if risk_scores else 0.5
        )
        
        # Test display content generation (Requirement 5.3, 5.4)
        dashboard.current_metrics = test_metrics
        display_content = dashboard._build_display_content()
        
        # Verify conflict predictions are displayed (Requirement 5.3)
        assert "CONFLICT PREDICTION" in display_content, "Display should include conflict prediction section"
        
        # Verify risk scores are displayed within valid range
        if test_metrics.current_risk_score is not None:
            risk_percentage = test_metrics.current_risk_score * 100
            assert f"{risk_percentage:.1f}%" in display_content, "Risk score percentage should be displayed"
            
            # Verify risk level indicators
            if test_metrics.current_risk_score > 0.7:
                assert "HIGH RISK" in display_content, "High risk should be indicated"
            elif test_metrics.current_risk_score > 0.5:
                assert "MODERATE" in display_content, "Moderate risk should be indicated"
            else:
                assert "LOW RISK" in display_content, "Low risk should be indicated"
        
        # Verify affected agents are displayed (Requirement 5.4)
        if conflict_analyses:
            for analysis in conflict_analyses:
                if analysis.affected_agents:
                    # At least one affected agent should appear in display
                    agent_found = any(agent in display_content for agent in analysis.affected_agents)
                    assert agent_found, f"Affected agents {analysis.affected_agents} should be displayed"
        
        # Verify automatic update capability (Requirement 5.5)
        # Test that metrics collection works without user input
        mock_system = self.create_mock_system_components()
        with patch('src.prediction_engine.cli_dashboard.conflict_predictor_system', mock_system):
            collected_metrics = dashboard._collect_metrics()
            assert collected_metrics is not None, "Metrics should be collected automatically"
            assert hasattr(collected_metrics, 'timestamp'), "Metrics should have timestamp"
            assert isinstance(collected_metrics.timestamp, datetime), "Timestamp should be datetime object"
    
    @given(
        intervention_data=st.lists(
            st.tuples(
                st.text(min_size=1, max_size=8, alphabet='abcdefghijklmnopqrstuvwxyz0123456789_'),  # target_agent
                st.sampled_from(["quarantine", "warning", "throttle"]),  # action_type
                st.text(min_size=5, max_size=30, alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ._-'),  # reason
                st.floats(min_value=0.5, max_value=1.0)  # confidence
            ),
            min_size=1,
            max_size=3
        )
    )
    @settings(max_examples=10, deadline=3000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_intervention_actions_display_with_justifications(self, intervention_data):
        """
        Property: For any intervention actions, the CLI should display quarantine 
        actions and their justifications automatically without user input.
        
        **Feature: agent-conflict-predictor, Property 8: Real-time CLI updates**
        **Validates: Requirements 5.4, 5.5**
        """
        dashboard = CLIDashboard()
        
        # Create intervention actions from test data
        interventions = []
        for target_agent, action_type, reason, confidence in intervention_data:
            intervention = InterventionAction(
                action_type=action_type,
                target_agent=target_agent,
                reason=reason,
                confidence=confidence,
                timestamp=datetime.now()
            )
            interventions.append(intervention)
        
        # Test metrics with intervention data
        test_metrics = self.create_test_dashboard_metrics(
            recent_interventions=interventions
        )
        
        # Test display content generation (Requirement 5.4, 5.5)
        dashboard.current_metrics = test_metrics
        display_content = dashboard._build_display_content()
        
        # Verify interventions are displayed (Requirement 5.4)
        assert "RECENT INTERVENTIONS" in display_content, "Display should include interventions section"
        
        if interventions:
            # The CLI dashboard only shows the most recent interventions up to max_display_items
            # and formats them in a specific way, so we need to check for the overall structure
            
            # Check that intervention statistics are shown
            total_interventions = len(interventions)
            quarantine_count = sum(1 for i in interventions if i.action_type == "quarantine")
            assert f"Total: {total_interventions}" in display_content, "Total interventions should be displayed"
            assert f"Quarantines: {quarantine_count}" in display_content, "Quarantine count should be displayed"
            
            # Check that at least some intervention details are shown
            # The dashboard shows recent interventions with specific formatting
            intervention_details_found = False
            
            for intervention in interventions[-10:]:  # Check recent interventions
                # Check for action type (formatted as uppercase)
                action_type_upper = intervention.action_type.upper()
                if action_type_upper in display_content:
                    intervention_details_found = True
                
                # Check for target agent (formatted with padding)
                target_padded = f"{intervention.target_agent:10s}"
                if intervention.target_agent in display_content or target_padded in display_content:
                    intervention_details_found = True
                
                # Check for confidence (formatted as integer percentage)
                confidence_pct = int(intervention.confidence * 100)
                confidence_patterns = [f"({confidence_pct:3.0f}%)", f"({confidence_pct}%)", f" {confidence_pct}%"]
                if any(pattern in display_content for pattern in confidence_patterns):
                    intervention_details_found = True
                
                # Check for reason/justification
                if intervention.reason and len(intervention.reason.strip()) > 0:
                    # Reason might be truncated to 60 characters
                    reason_truncated = intervention.reason[:60]
                    if reason_truncated in display_content:
                        intervention_details_found = True
            
            assert intervention_details_found, (
                "At least some intervention details should be displayed in the formatted output"
            )
        
        # Verify automatic update capability (Requirement 5.5)
        # Test that intervention section is built without user input
        interventions_section = dashboard._build_interventions_status()
        assert isinstance(interventions_section, list), "Interventions section should be a list of strings"
        assert len(interventions_section) > 0, "Interventions section should have content"
        
        # Verify section header is present
        assert interventions_section[0] == "RECENT INTERVENTIONS:", "Section should have proper header"
    
    @given(
        system_states=st.lists(
            st.tuples(
                st.booleans(),  # system_running
                st.integers(min_value=0, max_value=10),  # total_agents
                st.integers(min_value=0, max_value=10),  # active_agents
                st.integers(min_value=0, max_value=5),  # quarantined_agents
                st.floats(min_value=0.0, max_value=1.0)  # current_risk_score
            ),
            min_size=2,
            max_size=3
        )
    )
    @settings(max_examples=10, deadline=3000, suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much])
    def test_system_state_changes_reflect_immediately(self, system_states):
        """
        Property: For any system state change (predictions, interventions, agent status), 
        the CLI should display updates automatically without user input.
        
        **Feature: agent-conflict-predictor, Property 8: Real-time CLI updates**
        **Validates: Requirements 5.3, 5.4, 5.5**
        """
        assume(all(active <= total for _, total, active, _, _ in system_states))
        assume(all(quarantined <= total for _, total, _, quarantined, _ in system_states))
        
        dashboard = CLIDashboard()
        
        # Test each system state by creating metrics and verifying display
        for running, total, active, quarantined, risk in system_states:
            # Create test metrics for this state
            test_metrics = self.create_test_dashboard_metrics(
                system_running=running,
                total_agents=total,
                active_agents=active,
                quarantined_agents=quarantined,
                current_risk_score=risk
            )
            
            # Test display content generation (Requirements 5.3, 5.4, 5.5)
            dashboard.current_metrics = test_metrics
            display_content = dashboard._build_display_content()
            
            # Verify system status is displayed (Requirement 5.3)
            assert "SYSTEM STATUS" in display_content, "Display should include system status section"
            
            # Verify system running status
            if running:
                assert "🟢 RUNNING" in display_content, "Running status should be displayed"
            else:
                assert "🔴 STOPPED" in display_content, "Stopped status should be displayed"
            
            # Verify agent counts are displayed (Requirement 5.4)
            assert f"Total Agents: {total}" in display_content, "Total agents should be displayed"
            assert f"Active Agents: {active}" in display_content, "Active agents should be displayed"
            assert f"Quarantined Agents: {quarantined}" in display_content, "Quarantined agents should be displayed"
            
            # Verify risk score is displayed if present (Requirement 5.3)
            if risk is not None:
                risk_percentage = risk * 100
                assert f"{risk_percentage:.1f}%" in display_content, "Risk percentage should be displayed"
        
        # Verify automatic update capability (Requirement 5.5)
        # Test that system status section is built without user input
        system_section = dashboard._build_system_status()
        assert isinstance(system_section, list), "System status section should be a list of strings"
        assert len(system_section) > 0, "System status section should have content"
        assert system_section[0] == "SYSTEM STATUS:", "Section should have proper header"
        
        # Test that agent status section is built without user input
        agent_section = dashboard._build_agent_status()
        assert isinstance(agent_section, list), "Agent status section should be a list of strings"
        assert len(agent_section) > 0, "Agent status section should have content"
        assert agent_section[0] == "AGENT STATUS:", "Section should have proper header"
    
    @given(
        agent_trust_scores=st.dictionaries(
            st.text(min_size=1, max_size=8, alphabet='abcdefghijklmnopqrstuvwxyz0123456789_'),
            st.integers(min_value=0, max_value=100),
            min_size=1,
            max_size=5
        ),
        resource_utilizations=st.dictionaries(
            st.sampled_from(["cpu", "memory", "network", "storage", "database"]),
            st.floats(min_value=0.0, max_value=1.0),
            min_size=1,
            max_size=3
        )
    )
    @settings(max_examples=10, deadline=3000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_agent_status_and_metrics_display_updates(self, agent_trust_scores, resource_utilizations):
        """
        Property: For any agent status changes and resource metrics, the CLI 
        should display current information automatically without user input.
        
        **Feature: agent-conflict-predictor, Property 8: Real-time CLI updates**
        **Validates: Requirements 5.3, 5.4, 5.5**
        """
        dashboard = CLIDashboard()
        
        # Test metrics with agent and resource data
        test_metrics = self.create_test_dashboard_metrics(
            trust_scores=agent_trust_scores,
            resource_utilization=resource_utilizations
        )
        
        # Test display content generation (Requirements 5.3, 5.4, 5.5)
        dashboard.current_metrics = test_metrics
        display_content = dashboard._build_display_content()
        
        # Verify agent status is displayed (Requirement 5.4)
        assert "AGENT STATUS" in display_content, "Display should include agent status section"
        
        if agent_trust_scores:
            # Verify trust scores are displayed
            for agent_id, trust_score in agent_trust_scores.items():
                assert agent_id in display_content, f"Agent {agent_id} should be displayed"
                assert str(trust_score) in display_content, f"Trust score {trust_score} should be displayed"
                
                # Verify trust score indicators
                if trust_score < 30:
                    assert "⚠️" in display_content, "Low trust score warning should be displayed"
                else:
                    assert "✅" in display_content, "Good trust score indicator should be displayed"
        
        # Verify resource utilization is displayed (Requirement 5.3)
        assert "RESOURCE UTILIZATION" in display_content, "Display should include resource utilization section"
        
        if resource_utilizations:
            for resource_type, utilization in resource_utilizations.items():
                assert resource_type in display_content, f"Resource type {resource_type} should be displayed"
                
                # Verify utilization percentage
                percentage = utilization * 100
                assert f"{percentage:.1f}%" in display_content, f"Utilization {percentage:.1f}% should be displayed"
                
                # Verify utilization indicators
                if utilization > 0.8:
                    assert "🔴" in display_content, "High utilization warning should be displayed"
                elif utilization > 0.6:
                    assert "🟡" in display_content, "Medium utilization warning should be displayed"
                else:
                    assert "🟢" in display_content, "Low utilization indicator should be displayed"
        
        # Verify automatic update capability (Requirement 5.5)
        # Test that agent status section is built without user input
        agent_section = dashboard._build_agent_status()
        assert isinstance(agent_section, list), "Agent status section should be a list of strings"
        assert len(agent_section) > 0, "Agent status section should have content"
        assert agent_section[0] == "AGENT STATUS:", "Section should have proper header"
        
        # Test that resource status section is built without user input
        resource_section = dashboard._build_resource_status()
        assert isinstance(resource_section, list), "Resource status section should be a list of strings"
        assert len(resource_section) > 0, "Resource status section should have content"
        assert resource_section[0] == "RESOURCE UTILIZATION:", "Section should have proper header"
    
    def test_edge_case_no_system_data_available(self):
        """
        Test edge case: CLI should handle gracefully when no system data is available.
        
        **Feature: agent-conflict-predictor, Property 8: Real-time CLI updates**
        **Validates: Requirements 5.5**
        """
        dashboard = CLIDashboard()
        
        # Mock system that returns empty/error data
        mock_system = Mock()
        mock_system.get_system_status.side_effect = Exception("System unavailable")
        mock_system.agent_network = None
        mock_system.trust_manager = None
        mock_system.intervention_engine = None
        
        display_updates = []
        original_collect_metrics = dashboard._collect_metrics
        
        def track_empty_metrics():
            try:
                metrics = original_collect_metrics()
                display_updates.append(metrics)
                return metrics
            except Exception as e:
                # Should handle errors gracefully
                display_updates.append(None)
                return None
        
        dashboard._collect_metrics = track_empty_metrics
        
        with patch('src.prediction_engine.cli_dashboard.conflict_predictor_system', mock_system):
            dashboard.refresh_interval = 0.2
            dashboard.start()
            
            try:
                time.sleep(0.6)  # Wait for a few update cycles
                
                # Verify dashboard continues to update even with no data
                assert len(display_updates) > 0, "Dashboard should attempt updates even with no system data"
                
                # Dashboard should not crash and should continue running
                assert dashboard.is_running, "Dashboard should continue running despite system errors"
            
            finally:
                dashboard.stop()
    
    def test_edge_case_rapid_state_changes(self):
        """
        Test edge case: CLI should handle rapid system state changes correctly.
        
        **Feature: agent-conflict-predictor, Property 8: Real-time CLI updates**
        **Validates: Requirements 5.3, 5.4, 5.5**
        """
        dashboard = CLIDashboard()
        
        # Test rapid state changes by creating multiple different metrics
        state_changes = [
            self.create_test_dashboard_metrics(system_running=True, total_agents=5, active_agents=3),
            self.create_test_dashboard_metrics(system_running=False, total_agents=6, active_agents=4),
            self.create_test_dashboard_metrics(system_running=True, total_agents=7, active_agents=5),
            self.create_test_dashboard_metrics(system_running=False, total_agents=8, active_agents=6),
        ]
        
        # Test that each state change can be properly displayed (Requirements 5.3, 5.4, 5.5)
        for i, metrics in enumerate(state_changes):
            dashboard.current_metrics = metrics
            display_content = dashboard._build_display_content()
            
            # Verify each state is properly displayed
            assert "SYSTEM STATUS" in display_content, f"State {i}: System status should be displayed"
            assert f"Total Agents: {metrics.total_agents}" in display_content, f"State {i}: Total agents should be displayed"
            assert f"Active Agents: {metrics.active_agents}" in display_content, f"State {i}: Active agents should be displayed"
            
            # Verify system running status
            if metrics.system_running:
                assert "🟢 RUNNING" in display_content, f"State {i}: Running status should be displayed"
            else:
                assert "🔴 STOPPED" in display_content, f"State {i}: Stopped status should be displayed"
        
        # Verify automatic update capability handles state changes (Requirement 5.5)
        # Test that display content changes when metrics change
        dashboard.current_metrics = state_changes[0]
        content1 = dashboard._build_display_content()
        
        dashboard.current_metrics = state_changes[1]
        content2 = dashboard._build_display_content()
        
        # Content should be different for different states
        assert content1 != content2, "Display content should change when metrics change"
        
        # Test that header is consistently generated
        header1 = dashboard._build_header()
        header2 = dashboard._build_header()
        
        # Headers should have consistent format (though timestamps will differ)
        assert "CHORUS AGENT CONFLICT PREDICTOR - DASHBOARD" in header1, "Header should have consistent title"
        assert "CHORUS AGENT CONFLICT PREDICTOR - DASHBOARD" in header2, "Header should have consistent title"
        assert "Last Update:" in header1, "Header should include timestamp"
        assert "Last Update:" in header2, "Header should include timestamp"
    
    def test_dashboard_lifecycle_updates(self):
        """
        Test that dashboard updates work correctly through start/stop cycles.
        
        **Feature: agent-conflict-predictor, Property 8: Real-time CLI updates**
        **Validates: Requirements 5.5**
        """
        dashboard = CLIDashboard()
        mock_system = self.create_mock_system_components()
        
        # Test multiple start/stop cycles
        for cycle in range(3):
            updates_in_cycle = []
            
            def track_cycle_updates():
                updates_in_cycle.append(datetime.now())
            
            # Mock display methods to prevent terminal output
            dashboard._update_display = track_cycle_updates
            dashboard._clear_screen = Mock()
            dashboard._hide_cursor = Mock()
            dashboard._show_cursor = Mock()
            
            with patch('src.prediction_engine.cli_dashboard.conflict_predictor_system', mock_system):
                # Start dashboard
                dashboard.refresh_interval = 0.2
                dashboard.start()
                assert dashboard.is_running, f"Cycle {cycle}: Dashboard should be running"
                
                # Wait for updates
                time.sleep(0.6)
                
                # Stop dashboard
                dashboard.stop()
                assert not dashboard.is_running, f"Cycle {cycle}: Dashboard should be stopped"
                
                # Verify updates occurred during this cycle
                assert len(updates_in_cycle) > 0, f"Cycle {cycle}: Updates should occur while running"
                
                # Brief pause between cycles
                time.sleep(0.1)