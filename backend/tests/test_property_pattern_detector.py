"""
Property-based tests for Pattern Detection Engine.

**Feature: Advanced Pattern Detection**
**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**
"""
import pytest
from hypothesis import given, strategies as st
from src.prediction_engine.pattern_detector import PatternDetector
from src.mapper.models import GraphMetrics

class TestPatternDetector:
    
    @given(
        adjustments=st.lists(st.integers(min_value=-20, max_value=-11), min_size=5, max_size=10)
    )
    def test_property_resource_hoarding_detection(self, adjustments):
        """
        Property 12a: Resource hoarding detection.
        Validates: Requirement 5.3
        """
        detector = PatternDetector()
        history = [{"adjustment": adj} for adj in adjustments]
        
        # Should detect because all are high consumption (<-10)
        assert detector.detect_resource_hoarding("test_agent", history) is True

    @given(
        density=st.floats(min_value=0.81, max_value=1.0),
        node_count=st.integers(min_value=6, max_value=100)
    )
    def test_property_cascade_detection(self, density, node_count):
        """
        Property 12b: Cascade detection.
        Validates: Requirement 5.4
        """
        detector = PatternDetector()
        metrics = GraphMetrics(
            node_count=node_count,
            edge_count=100,
            density=density,
            clustering_coefficient=0.5,
            detected_loops=[],
            quarantined_nodes=0
        )
        
        assert detector.detect_communication_cascade(metrics) is True

    @given(
        # Alternating positive/negative sequence
        seq_len=st.integers(min_value=4, max_value=10)
    )
    def test_property_byzantine_behavior_detection(self, seq_len):
        """
        Property 12c: Byzantine behavior detection.
        Validates: Requirement 5.5
        """
        detector = PatternDetector()
        # Create alternating history: 5, -5, 5, -5...
        adjustments = [5 if i % 2 == 0 else -5 for i in range(seq_len)]
        history = [{"adjustment": adj} for adj in adjustments]
        
        # 4 items: 5, -5, 5, -5 -> flips: (5,-5), (-5,5), (5,-5) = 3 flips.
        # Threshold is >= 3 flips.
        should_detect = (len(adjustments) >= 4)
        
        assert detector.detect_byzantine_behavior("test_agent", history) == should_detect
