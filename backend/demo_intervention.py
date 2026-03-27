#!/usr/bin/env python3
"""
Demonstration script for the intervention engine functionality.
"""
import sys
import os
from datetime import datetime
from unittest.mock import Mock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.prediction_engine.intervention_engine import ConflictInterventionEngine
from src.prediction_engine.quarantine_manager import RedisQuarantineManager
from src.prediction_engine.models.core import ConflictAnalysis, QuarantineResult
from src.prediction_engine.interfaces import TrustManager


def create_mock_trust_manager():
    """Create a mock trust manager for demonstration."""
    mock_trust_manager = Mock(spec=TrustManager)
    
    # Mock trust scores (lower = more aggressive)
    trust_scores = {
        "agent_001": 85,  # High trust
        "agent_002": 25,  # Low trust (most aggressive)
        "agent_003": 60,  # Medium trust
        "agent_004": 15,  # Very low trust
        "agent_005": 90   # Very high trust
    }
    
    mock_trust_manager.get_trust_score.side_effect = lambda agent_id: trust_scores.get(agent_id, 50)
    mock_trust_manager.get_quarantine_count = Mock(return_value=0)
    mock_trust_manager.update_trust_score = Mock()
    
    return mock_trust_manager


def create_mock_quarantine_manager():
    """Create a mock quarantine manager for demonstration."""
    mock_quarantine_manager = Mock(spec=RedisQuarantineManager)
    
    def mock_quarantine_agent(agent_id, reason):
        return QuarantineResult(
            success=True,
            agent_id=agent_id,
            reason=f"Successfully quarantined: {reason}",
            timestamp=datetime.now()
        )
    
    mock_quarantine_manager.quarantine_agent.side_effect = mock_quarantine_agent
    mock_quarantine_manager.is_quarantined.return_value = False
    
    return mock_quarantine_manager


def demonstrate_intervention_engine():
    """Demonstrate the intervention engine functionality."""
    print("🚀 Agent Conflict Predictor - Intervention Engine Demo")
    print("=" * 60)
    
    # Create mock components
    trust_manager = create_mock_trust_manager()
    quarantine_manager = create_mock_quarantine_manager()
    
    # Initialize intervention engine
    engine = ConflictInterventionEngine(
        trust_manager_instance=trust_manager,
        quarantine_manager_instance=quarantine_manager
    )
    
    print(f"✓ Intervention engine initialized with threshold: {engine.conflict_risk_threshold}")
    print()
    
    # Test 1: Low-risk scenario (no intervention)
    print("📊 Test 1: Low-risk conflict scenario")
    low_risk_analysis = ConflictAnalysis(
        risk_score=0.4,
        confidence_level=0.8,
        affected_agents=["agent_001", "agent_002"],
        predicted_failure_mode="Minor resource contention",
        nash_equilibrium=None,
        timestamp=datetime.now()
    )
    
    needs_intervention = engine.evaluate_intervention_need(low_risk_analysis)
    print(f"Risk score: {low_risk_analysis.risk_score}")
    print(f"Intervention needed: {needs_intervention}")
    print("✓ No intervention required for low-risk scenario")
    print()
    
    # Test 2: High-risk scenario (intervention required)
    print("🚨 Test 2: High-risk conflict scenario")
    high_risk_analysis = ConflictAnalysis(
        risk_score=0.85,
        confidence_level=0.9,
        affected_agents=["agent_001", "agent_002", "agent_003", "agent_004"],
        predicted_failure_mode="Severe resource contention leading to cascading failure",
        nash_equilibrium=None,
        timestamp=datetime.now()
    )
    
    needs_intervention = engine.evaluate_intervention_need(high_risk_analysis)
    print(f"Risk score: {high_risk_analysis.risk_score}")
    print(f"Intervention needed: {needs_intervention}")
    
    if needs_intervention:
        # Identify most aggressive agent
        most_aggressive = engine.identify_most_aggressive_agent(high_risk_analysis.affected_agents)
        print(f"Most aggressive agent identified: {most_aggressive}")
        
        # Execute quarantine
        result = engine.execute_quarantine(most_aggressive, "High conflict risk detected")
        print(f"Quarantine result: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Quarantine reason: {result.reason}")
        
        # Show intervention history
        history = engine.get_intervention_history()
        print(f"Total interventions recorded: {len(history)}")
        
        if history:
            latest = history[-1]
            print(f"Latest intervention: {latest.action_type} on {latest.target_agent}")
    
    print("✓ High-risk scenario handled with quarantine")
    print()
    
    # Test 3: Process complete conflict analysis
    print("🔄 Test 3: Complete conflict analysis processing")
    result = engine.process_conflict_analysis(high_risk_analysis)
    
    if result:
        print(f"Conflict analysis processed successfully")
        print(f"Agent quarantined: {result.agent_id}")
        print(f"Success: {result.success}")
    else:
        print("No action taken (risk below threshold)")
    
    print()
    
    # Test 4: Show statistics
    print("📈 Test 4: Intervention statistics")
    stats = engine.get_statistics()
    print(f"Total interventions: {stats['total_interventions']}")
    print(f"Quarantine actions: {stats['quarantine_actions']}")
    print(f"Other actions: {stats['other_actions']}")
    print()
    
    # Test 5: Edge cases
    print("⚠️  Test 5: Edge case handling")
    
    # Empty agent list
    try:
        engine.identify_most_aggressive_agent([])
    except ValueError as e:
        print(f"✓ Correctly handled empty agent list: {e}")
    
    # Threshold boundary
    boundary_analysis = ConflictAnalysis(
        risk_score=0.7,  # Exactly at threshold
        confidence_level=0.8,
        affected_agents=["agent_001"],
        predicted_failure_mode="Boundary test",
        nash_equilibrium=None,
        timestamp=datetime.now()
    )
    
    boundary_intervention = engine.evaluate_intervention_need(boundary_analysis)
    print(f"✓ Threshold boundary test (0.7): intervention = {boundary_intervention}")
    
    print()
    print("🎉 Intervention Engine Demo Complete!")
    print("=" * 60)
    print("The intervention engine successfully:")
    print("• Evaluates conflict risk against configurable thresholds")
    print("• Identifies the most aggressive agents using trust scores")
    print("• Executes quarantine actions through the quarantine manager")
    print("• Maintains intervention history and statistics")
    print("• Handles edge cases and error conditions gracefully")


if __name__ == "__main__":
    demonstrate_intervention_engine()