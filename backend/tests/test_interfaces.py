"""
Tests for the core interfaces and data models.
"""
import pytest
from datetime import datetime
from src.prediction_engine.models.core import (
    AgentIntention, AgentMessage, ConflictAnalysis, TrustScoreEntry,
    ResourceRequest, MessageType, ResourceType
)
from src.prediction_engine.interfaces import (
    Agent, GeminiClient, TrustManager, InterventionEngine
)


class TestCoreDataModels:
    """Test core data model creation and validation."""
    
    def test_agent_intention_creation(self):
        """Test creating an AgentIntention instance."""
        intention = AgentIntention(
            agent_id="test_agent",
            resource_type="cpu",
            requested_amount=50,
            priority_level=1,
            timestamp=datetime.now()
        )
        
        assert intention.agent_id == "test_agent"
        assert intention.resource_type == "cpu"
        assert intention.requested_amount == 50
        assert intention.priority_level == 1
        assert isinstance(intention.timestamp, datetime)
    
    def test_conflict_analysis_creation(self):
        """Test creating a ConflictAnalysis instance."""
        analysis = ConflictAnalysis(
            risk_score=0.75,
            confidence_level=0.9,
            affected_agents=["agent1", "agent2"],
            predicted_failure_mode="resource_contention",
            nash_equilibrium=None,
            timestamp=datetime.now()
        )
        
        assert analysis.risk_score == 0.75
        assert analysis.confidence_level == 0.9
        assert len(analysis.affected_agents) == 2
        assert analysis.predicted_failure_mode == "resource_contention"
    
    def test_trust_score_entry_creation(self):
        """Test creating a TrustScoreEntry instance."""
        now = datetime.now()
        entry = TrustScoreEntry(
            agent_id="test_agent",
            current_score=85,
            last_updated=now,
            adjustment_history=[],
            quarantine_count=0,
            creation_time=now
        )
        
        assert entry.agent_id == "test_agent"
        assert entry.current_score == 85
        assert entry.quarantine_count == 0


class TestInterfaceDefinitions:
    """Test that interfaces are properly defined."""
    
    def test_agent_interface_methods(self):
        """Test that Agent interface has required methods."""
        # Check that Agent is abstract and has required methods
        assert hasattr(Agent, 'make_resource_request')
        assert hasattr(Agent, 'receive_message')
        assert hasattr(Agent, 'get_current_intentions')
        
        # Verify it's abstract
        with pytest.raises(TypeError):
            Agent("test_agent")
    
    def test_gemini_client_interface_methods(self):
        """Test that GeminiClient interface has required methods."""
        assert hasattr(GeminiClient, 'analyze_conflict_risk')
        assert hasattr(GeminiClient, 'calculate_nash_equilibrium')
        
        # Verify it's abstract
        with pytest.raises(TypeError):
            GeminiClient("fake_api_key")
    
    def test_trust_manager_interface_methods(self):
        """Test that TrustManager interface has required methods."""
        assert hasattr(TrustManager, 'get_trust_score')
        assert hasattr(TrustManager, 'update_trust_score')
        assert hasattr(TrustManager, 'check_quarantine_threshold')
        assert hasattr(TrustManager, 'get_all_trust_scores')
        
        # Verify it's abstract
        with pytest.raises(TypeError):
            TrustManager()
    
    def test_intervention_engine_interface_methods(self):
        """Test that InterventionEngine interface has required methods."""
        assert hasattr(InterventionEngine, 'evaluate_intervention_need')
        assert hasattr(InterventionEngine, 'execute_quarantine')
        assert hasattr(InterventionEngine, 'identify_most_aggressive_agent')
        
        # Verify it's abstract
        with pytest.raises(TypeError):
            InterventionEngine()


class TestEnumDefinitions:
    """Test enum definitions."""
    
    def test_message_type_enum(self):
        """Test MessageType enum values."""
        assert MessageType.RESOURCE_REQUEST.value == "resource_request"
        assert MessageType.RESOURCE_RESPONSE.value == "resource_response"
        assert MessageType.STATUS_UPDATE.value == "status_update"
        assert MessageType.HEARTBEAT.value == "heartbeat"
    
    def test_resource_type_enum(self):
        """Test ResourceType enum values."""
        assert ResourceType.CPU.value == "cpu"
        assert ResourceType.MEMORY.value == "memory"
        assert ResourceType.NETWORK.value == "network"
        assert ResourceType.STORAGE.value == "storage"
        assert ResourceType.DATABASE.value == "database"