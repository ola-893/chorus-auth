
import pytest
from hypothesis import given, strategies as st
from src.stream_analytics import MetricsAggregator

class TestPropertyAnalytics:
    @given(st.lists(st.floats(min_value=0, max_value=1000), min_size=1))
    def test_latency_calculation_property(self, latencies):
        """Property: Average latency should always be between min and max of input latencies."""
        aggregator = MetricsAggregator(window_size=100)
        for l in latencies:
            aggregator.record_latency(l)
            
        metrics = aggregator.calculate_metrics()
        
        if not latencies:
            return

        avg = metrics["avg_latency_ms"]
        # Rounding in MetricsAggregator (round(x, 2)) causes issues with exact comparison
        # We should check if it's within a small epsilon of the bounds, or relax the check slightly
        # Since we rounded to 2 decimal places, the error is at most 0.005
        assert min(latencies) - 0.01 <= avg <= max(latencies) + 0.01

    @given(st.lists(st.integers(min_value=0, max_value=1), min_size=10))
    def test_error_rate_calculation(self, operations):
        """Property: Error rate should be error_count / total_count."""
        aggregator = MetricsAggregator(window_size=100)
        error_count = 0
        for op in operations:
            aggregator.record_message()
            if op == 1:
                aggregator.record_error()
                error_count += 1
                
        metrics = aggregator.calculate_metrics()
        
        expected_rate = error_count / len(operations)
        # Allow small floating point difference
        assert abs(metrics["error_rate"] - expected_rate) < 0.0001
