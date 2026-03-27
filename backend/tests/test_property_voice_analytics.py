
import pytest
from hypothesis import given, strategies as st
import time
from src.prediction_engine.voice_analytics import VoiceAlertAnalytics

class TestPropertyVoiceAnalytics:
    
    @given(st.lists(st.floats(min_value=1.0, max_value=60.0), min_size=1))
    def test_response_time_calculation(self, response_delays):
        """
        Property 7: Voice alert analytics completeness.
        Verify average response time calculation based on event stream.
        """
        analytics = VoiceAlertAnalytics()
        current_time = 1000.0
        
        for delay in response_delays:
            # Simulate Alert
            analytics._on_alert_generated({"timestamp": current_time, "alert_title": "test"})
            
            # Simulate Intervention after delay
            intervention_time = current_time + delay
            # Analytics expects isoformat string or uses raw timestamp if passed?
            # The implementation converts isoformat string to timestamp.
            # Let's mock the data format correctly for _on_intervention
            from datetime import datetime
            
            # We need to construct a valid ISO string corresponding to the timestamp
            # Or assume the analytics class handles floats if we modified it?
            # Looking at implementation: 
            # timestamp = datetime.fromisoformat(data.get("timestamp", ...)).timestamp()
            
            # So we must provide ISO string
            dt_obj = datetime.fromtimestamp(intervention_time)
            analytics._on_intervention({"timestamp": dt_obj.isoformat()})
            
            current_time += 100 # Move forward
            
        avg = analytics.get_average_response_time()
        expected = sum(response_delays) / len(response_delays)
        
        assert abs(avg - expected) < 0.001

    @given(st.integers(min_value=0, max_value=50), st.integers(min_value=0, max_value=50))
    def test_success_rate(self, successes, failures):
        """Verify success rate calculation."""
        analytics = VoiceAlertAnalytics()
        total = successes + failures
        if total == 0:
            return

        for _ in range(total):
            analytics._on_alert_generated({"timestamp": time.time(), "alert_title": "req"})
            
        for _ in range(successes):
            analytics._on_voice_success({})
            
        rate = analytics.get_success_rate()
        expected = successes / total
        assert abs(rate - expected) < 0.001
