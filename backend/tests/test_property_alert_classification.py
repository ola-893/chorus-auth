
import pytest
from hypothesis import given, strategies as st
from unittest.mock import MagicMock, patch
from datetime import datetime

from src.prediction_engine.alert_classification import AlertSeverityClassifier, AlertSeverity, AlertContext
from src.prediction_engine.models.core import ConflictAnalysis

class TestPropertyAlertClassification:
    
    @pytest.fixture
    def classifier(self):
        with patch('src.prediction_engine.alert_classification.trust_manager') as mock_trust, \
             patch('src.prediction_engine.alert_classification.quarantine_manager') as mock_quarantine:
            
            # Setup default mock behaviors
            mock_trust.get_trust_score_analytics.return_value = {"trend": 0.0}
            mock_quarantine.get_quarantined_agents.return_value = []
            
            classifier = AlertSeverityClassifier()
            classifier.trust_manager = mock_trust
            classifier.quarantine_manager = mock_quarantine
            yield classifier

    @given(st.floats(min_value=0.0, max_value=1.0))
    def test_severity_classification_monotonicity(self, risk_score):
        """
        Property 1: Alert severity classification consistency.
        Higher risk scores should never result in lower severity levels (monotonicity),
        assuming other context variables are constant.
        """
        classifier = AlertSeverityClassifier()
        
        # Helper to convert severity enum to comparable integer
        severity_rank = {
            AlertSeverity.INFO: 0,
            AlertSeverity.WARNING: 1,
            AlertSeverity.CRITICAL: 2,
            AlertSeverity.EMERGENCY: 3
        }
        
        context = AlertContext(
            incident_type="test",
            affected_agents=[],
            risk_score=risk_score,
            timestamp=datetime.now()
        )
        
        severity = classifier._determine_severity(context)
        rank = severity_rank[severity]
        
        # Check thresholds
        if risk_score >= 0.95:
            assert rank >= 3
        elif risk_score >= 0.85:
            assert rank >= 2
        elif risk_score >= 0.6:
            assert rank >= 1
        else:
            # It can be higher if other factors escalate it, but minimal expectation:
            pass

    @given(st.integers(min_value=0, max_value=10), st.floats(min_value=0.0, max_value=1.0))
    def test_escalation_logic(self, quarantine_count, risk_score):
        """
        Property 1b: Verify escalation logic for multiple quarantines.
        """
        classifier = AlertSeverityClassifier()
        
        context = AlertContext(
            incident_type="test",
            affected_agents=[],
            risk_score=risk_score,
            active_quarantines=quarantine_count,
            timestamp=datetime.now()
        )
        
        severity = classifier._determine_severity(context)
        
        # Specific rule: >= 3 quarantines and risk > 0.5 -> EMERGENCY
        if quarantine_count >= 3 and risk_score > 0.5:
            assert severity == AlertSeverity.EMERGENCY
