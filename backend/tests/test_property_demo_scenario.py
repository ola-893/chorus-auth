
import pytest
import time
from unittest.mock import MagicMock, patch
from src.prediction_engine.demo_scenario_engine import DemoScenarioEngine, DemoStep

class TestPropertyDemoScenario:
    
    @pytest.fixture
    def engine(self):
        engine = DemoScenarioEngine()
        # Reduce delays for testing
        for steps in engine.scenarios.values():
            for step in steps:
                step.delay = 0.01 
        return engine

    @patch('src.prediction_engine.demo_scenario_engine.voice_client')
    @patch('src.prediction_engine.demo_scenario_engine.alert_delivery_engine')
    def test_scenario_execution_completeness(self, mock_delivery, mock_voice, engine):
        """
        Property 5: Demo scenario execution completeness.
        Verify that all steps in a defined scenario are executed.
        """
        # Mock enabled voice
        mock_voice.enabled = True
        # Ensure the generate_alert method is a mock that we can assert on
        mock_voice.generate_alert = MagicMock()
        
        scenario_name = "routing_loop"
        steps = engine.scenarios[scenario_name]
        expected_narrations = sum(1 for s in steps if s.narration or s.template_key)
        expected_alerts = sum(1 for s in steps if s.alert)
        
        # Run synchronously for test logic (override threading behavior if possible, 
        # or just wait)
        # We'll just call _execute_steps directly to avoid race conditions in test
        engine.running = True
        engine._execute_steps(steps)
        
        assert mock_voice.generate_alert.call_count == expected_narrations
        assert mock_delivery.process_alert.call_count == expected_alerts
        assert engine.running is False # Should reset after finish

    def test_scenario_interruption(self, engine):
        """Test stopping a scenario mid-execution."""
        # Create a long running step
        steps = [DemoStep("start", 0.1), DemoStep("end", 0.1)]
        
        engine.running = True
        
        # We need to run this in a thread to interrupt it
        import threading
        t = threading.Thread(target=engine._execute_steps, args=(steps,))
        t.start()
        
        time.sleep(0.05) # Wait for start
        engine.stop_scenario() # Interrupt
        t.join()
        
        assert engine.running is False
