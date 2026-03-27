"""
Prediction engine module for agent conflict prediction.
"""

# Core interfaces
from .interfaces import (
    Agent, GeminiClient, TrustManager, InterventionEngine,
    ResourceManager, AgentNetwork, RedisClient, GameTheoryPromptBuilder,
    ConflictAnalysisParser, TrustScoreManager, QuarantineManager
)

# Data models
from .models.core import (
    AgentIntention, AgentMessage, ConflictAnalysis, QuarantineAction,
    TrustScoreEntry, GameState, EquilibriumSolution, InterventionAction,
    ResourceStatus, ContentionEvent, RequestResult, QuarantineResult,
    ResourceRequest, MessageType, ResourceType
)

# Implementations
from .gemini_client import GeminiClient as GeminiClientImpl
from .game_theory.prompt_builder import GameTheoryPromptBuilder as GameTheoryPromptBuilderImpl
from .analysis_parser import ConflictAnalysisParser as ConflictAnalysisParserImpl
from .redis_client import RedisClient as RedisClientImpl, redis_client
from .trust_manager import (
    TrustPolicy, RedisTrustScoreManager, RedisTrustManager, trust_manager
)
from .intervention_engine import ConflictInterventionEngine, intervention_engine
from .quarantine_manager import RedisQuarantineManager, quarantine_manager
from .simulator import SimulatedAgent, ResourceManager as ResourceManagerImpl, AgentNetwork as AgentNetworkImpl
from .system_integration import ConflictPredictorSystem, conflict_predictor_system

__all__ = [
    # Interfaces
    'Agent', 'GeminiClient', 'TrustManager', 'InterventionEngine',
    'ResourceManager', 'AgentNetwork', 'RedisClient', 'GameTheoryPromptBuilder',
    'ConflictAnalysisParser', 'TrustScoreManager', 'QuarantineManager',
    
    # Data models
    'AgentIntention', 'AgentMessage', 'ConflictAnalysis', 'QuarantineAction',
    'TrustScoreEntry', 'GameState', 'EquilibriumSolution', 'InterventionAction',
    'ResourceStatus', 'ContentionEvent', 'RequestResult', 'QuarantineResult',
    'ResourceRequest', 'MessageType', 'ResourceType',
    
    # Implementations
    'GeminiClientImpl', 'GameTheoryPromptBuilderImpl', 'ConflictAnalysisParserImpl',
    'RedisClientImpl', 'redis_client', 'TrustPolicy', 'RedisTrustScoreManager',
    'RedisTrustManager', 'trust_manager', 'ConflictInterventionEngine', 
    'intervention_engine', 'RedisQuarantineManager', 'quarantine_manager',
    'SimulatedAgent', 'ResourceManagerImpl', 'AgentNetworkImpl',
    'ConflictPredictorSystem', 'conflict_predictor_system'
]