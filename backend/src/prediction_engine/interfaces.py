"""
Base interfaces for the agent conflict predictor components.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from .models.core import (
    AgentIntention, AgentMessage, ConflictAnalysis, GameState,
    EquilibriumSolution, ResourceRequest, RequestResult, ResourceStatus,
    ContentionEvent, QuarantineResult, TrustScoreEntry
)


class Agent(ABC):
    """Base interface for autonomous agents."""
    
    def __init__(self, agent_id: str, initial_trust_score: int = 100):
        self.agent_id = agent_id
        self.trust_score = initial_trust_score
        self.is_quarantined = False
    
    @abstractmethod
    def make_resource_request(self, resource_type: str, amount: int) -> ResourceRequest:
        """Make a request for a shared resource."""
        pass
    
    @abstractmethod
    def receive_message(self, message: AgentMessage) -> None:
        """Receive and process a message from another agent."""
        pass
    
    @abstractmethod
    def get_current_intentions(self) -> List[AgentIntention]:
        """Get the agent's current intentions."""
        pass


class GeminiClient(ABC):
    """Interface for Google Gemini API client."""
    
    def __init__(self, api_key: str, model: str = "gemini-3-pro-preview"):
        self.api_key = api_key
        self.model = model
    
    @abstractmethod
    def analyze_conflict_risk(self, agent_intentions: List[AgentIntention]) -> ConflictAnalysis:
        """Analyze conflict risk using game theory."""
        pass
    
    @abstractmethod
    def calculate_nash_equilibrium(self, game_state: GameState) -> EquilibriumSolution:
        """Calculate Nash equilibrium for the given game state."""
        pass


class TrustManager(ABC):
    """Interface for managing agent trust scores."""
    
    @abstractmethod
    def get_trust_score(self, agent_id: str) -> int:
        """Get the current trust score for an agent."""
        pass
    
    @abstractmethod
    def update_trust_score(self, agent_id: str, adjustment: int, reason: str) -> None:
        """Update an agent's trust score."""
        pass
    
    @abstractmethod
    def check_quarantine_threshold(self, agent_id: str) -> bool:
        """Check if an agent should be quarantined based on trust score."""
        pass
    
    @abstractmethod
    def get_all_trust_scores(self) -> Dict[str, int]:
        """Get trust scores for all agents."""
        pass


class InterventionEngine(ABC):
    """Interface for the intervention engine."""
    
    @abstractmethod
    def evaluate_intervention_need(self, conflict_analysis: ConflictAnalysis) -> bool:
        """Evaluate if intervention is needed based on conflict analysis."""
        pass
    
    @abstractmethod
    def execute_quarantine(self, agent_id: str, reason: str) -> QuarantineResult:
        """Execute quarantine for a specific agent."""
        pass
    
    @abstractmethod
    def identify_most_aggressive_agent(self, agents: List[str]) -> str:
        """Identify the most aggressive agent from a list."""
        pass


class ResourceManager(ABC):
    """Interface for managing shared resources."""
    
    @abstractmethod
    def process_request(self, request: ResourceRequest) -> RequestResult:
        """Process a resource request."""
        pass
    
    @abstractmethod
    def get_resource_status(self, resource_type: str) -> ResourceStatus:
        """Get the current status of a resource."""
        pass
    
    @abstractmethod
    def detect_contention(self) -> List[ContentionEvent]:
        """Detect resource contention events."""
        pass


class AgentNetwork(ABC):
    """Interface for managing the agent network simulation."""
    
    @abstractmethod
    def create_agents(self, count: int) -> List[Agent]:
        """Create a specified number of agents."""
        pass
    
    @abstractmethod
    def start_simulation(self) -> None:
        """Start the agent simulation."""
        pass
    
    @abstractmethod
    def stop_simulation(self) -> None:
        """Stop the agent simulation."""
        pass
    
    @abstractmethod
    def get_active_agents(self) -> List[Agent]:
        """Get all currently active agents."""
        pass


class RedisClient(ABC):
    """Interface for Redis operations."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """Get a value from Redis."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set a value in Redis."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a key from Redis."""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if a key exists in Redis."""
        pass


class GameTheoryPromptBuilder(ABC):
    """Interface for building game theory prompts."""
    
    @abstractmethod
    def build_conflict_analysis_prompt(self, intentions: List[AgentIntention]) -> str:
        """Build a prompt for conflict analysis."""
        pass
    
    @abstractmethod
    def build_nash_equilibrium_prompt(self, game_state: GameState) -> str:
        """Build a prompt for Nash equilibrium calculation."""
        pass


class ConflictAnalysisParser(ABC):
    """Interface for parsing Gemini API responses."""
    
    @abstractmethod
    def parse_conflict_analysis(self, response: str) -> ConflictAnalysis:
        """Parse conflict analysis response from Gemini API."""
        pass
    
    @abstractmethod
    def parse_nash_equilibrium(self, response: str) -> EquilibriumSolution:
        """Parse Nash equilibrium response from Gemini API."""
        pass


class TrustScoreManager(ABC):
    """Interface for trust score management operations."""
    
    @abstractmethod
    def initialize_agent(self, agent_id: str) -> TrustScoreEntry:
        """Initialize trust score for a new agent."""
        pass
    
    @abstractmethod
    def adjust_score(self, agent_id: str, adjustment: int, reason: str) -> TrustScoreEntry:
        """Adjust an agent's trust score."""
        pass
    
    @abstractmethod
    def get_score_entry(self, agent_id: str) -> Optional[TrustScoreEntry]:
        """Get complete trust score entry for an agent."""
        pass


class QuarantineManager(ABC):
    """Interface for quarantine management."""
    
    @abstractmethod
    def quarantine_agent(self, agent_id: str, reason: str) -> QuarantineResult:
        """Quarantine a specific agent."""
        pass
    
    @abstractmethod
    def is_quarantined(self, agent_id: str) -> bool:
        """Check if an agent is currently quarantined."""
        pass
    
    @abstractmethod
    def release_quarantine(self, agent_id: str) -> QuarantineResult:
        """Release an agent from quarantine."""
        pass