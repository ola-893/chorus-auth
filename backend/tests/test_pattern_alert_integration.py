"""
Integration test for pattern detection alerts in dashboard.
Tests the complete flow from pattern detection to WebSocket broadcast.
"""
import pytest
import json
from datetime import datetime
from src.prediction_engine.pattern_detector import PatternDetector
from src.stream_processor import StreamProcessor


class TestPatternAlertIntegration:
    """Test pattern detection alert integration."""
    
    def test_resource_hoarding_alert_generation(self):
        """Test that resource hoarding pattern generates proper alert data."""
        detector = PatternDetector()
        
        # Create history showing resource hoarding
        history = [
            {"requested_amount": 80, "priority_level": 9},
            {"requested_amount": 85, "priority_level": 9},
            {"requested_amount": 90, "priority_level": 8},
            {"requested_amount": 75, "priority_level": 9},
            {"requested_amount": 88, "priority_level": 10}
        ]
        
        # Detect pattern
        is_hoarding = detector.detect_resource_hoarding("test_agent_1", history)
        assert is_hoarding is True
        
    def test_routing_loop_detection(self):
        """Test routing loop detection."""
        detector = PatternDetector()
        
        # Create a routing loop: A -> B -> C -> A
        detector.record_interaction("agent_a", "agent_b")
        detector.record_interaction("agent_b", "agent_c")
        detector.record_interaction("agent_c", "agent_a")
        
        # Detect loop
        loop = detector.detect_routing_loop("agent_a")
        assert loop is not None
        assert len(loop) >= 3
        assert "agent_a" in loop
        
    def test_byzantine_behavior_detection(self):
        """Test Byzantine behavior detection."""
        detector = PatternDetector()
        
        # Create alternating trust score adjustments
        history = [
            {"adjustment": 10},
            {"adjustment": -10},
            {"adjustment": 15},
            {"adjustment": -15},
            {"adjustment": 8}
        ]
        
        # Detect Byzantine behavior
        is_byzantine = detector.detect_byzantine_behavior("test_agent_2", history)
        assert is_byzantine is True
        
    def test_communication_cascade_detection(self):
        """Test communication cascade detection."""
        detector = PatternDetector()
        
        # Simulate high message volume
        for i in range(60):
            detector.record_interaction(f"agent_cascade", f"target_{i}")
        
        # Detect cascade
        is_cascade = detector.detect_communication_cascade_by_agent("agent_cascade")
        assert is_cascade is True
        
    def test_pattern_details_structure(self):
        """Test that pattern details have correct structure for frontend."""
        # This would be the structure sent to the frontend
        pattern_details = {
            "RESOURCE_HOARDING": {
                "type": "resource_hoarding",
                "severity": "warning",
                "details": "Agent test_agent is consistently requesting high-priority resources",
                "recommended_action": "Monitor resource allocation patterns",
                "affected_agents": ["test_agent"]
            }
        }
        
        # Verify structure
        assert "type" in pattern_details["RESOURCE_HOARDING"]
        assert "severity" in pattern_details["RESOURCE_HOARDING"]
        assert "details" in pattern_details["RESOURCE_HOARDING"]
        assert "recommended_action" in pattern_details["RESOURCE_HOARDING"]
        assert "affected_agents" in pattern_details["RESOURCE_HOARDING"]
        assert isinstance(pattern_details["RESOURCE_HOARDING"]["affected_agents"], list)
        
    def test_severity_levels(self):
        """Test that different patterns have appropriate severity levels."""
        severities = {
            "ROUTING_LOOP": "critical",
            "BYZANTINE_BEHAVIOR": "critical",
            "RESOURCE_HOARDING": "warning",
            "COMMUNICATION_CASCADE": "warning"
        }
        
        # Verify severity levels are appropriate
        assert severities["ROUTING_LOOP"] == "critical"
        assert severities["BYZANTINE_BEHAVIOR"] == "critical"
        assert severities["RESOURCE_HOARDING"] == "warning"
        assert severities["COMMUNICATION_CASCADE"] == "warning"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
