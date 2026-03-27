
import pytest
import time
from src.stream_analytics import MetricsAggregator

class TestStreamAnalytics:
    @pytest.fixture
    def aggregator(self):
        return MetricsAggregator(window_size=10)

    def test_real_time_metrics_calculation(self, aggregator):
        """Test calculation of real-time metrics (Property 16)."""
        # Simulate some data
        start_time = time.time()
        aggregator.record_message()
        aggregator.record_latency(100)
        aggregator.record_message()
        aggregator.record_latency(200)
        aggregator.record_error()
        
        metrics = aggregator.calculate_metrics()
        
        # Throughput: 2 messages in window
        assert metrics["throughput"] > 0
        assert metrics["avg_latency_ms"] == 150.0
        assert metrics["max_latency_ms"] == 200.0
        assert metrics["error_rate"] == 0.5 # 1 error / 2 messages? Or 1 error event?
        # Implementation of error rate: error_count / msg_count. 
        # Here msg_count is 2 (from record_message). error_count is 1.
        
    def test_statistical_anomaly_detection(self, aggregator):
        """Test detection of anomalies (Property 17)."""
        # Simulate normal behavior
        aggregator.record_latency(50)
        
        anomalies = aggregator.detect_anomalies()
        assert len(anomalies) == 0
        
        # Simulate spike
        for _ in range(5):
            aggregator.record_latency(600) 
        
        # Force recalc
        aggregator._last_calc_time = 0 
        
        anomalies = aggregator.detect_anomalies()
        assert any("High Latency" in a for a in anomalies)

    def test_aggregated_statistics_generation(self, aggregator):
        """Test generation of comprehensive stats (Property 18)."""
        aggregator.record_message()
        aggregator.record_resource_usage("cpu", 15000) # Bottleneck threshold 10000
        
        stats = aggregator.get_aggregated_statistics()
        
        assert "throughput" in stats
        assert "bottlenecks" in stats
        assert any("Resource Constraint" in b for b in stats["bottlenecks"])
