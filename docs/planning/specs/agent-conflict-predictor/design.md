# Agent Conflict Predictor Design Document

## Overview

The Agent Conflict Predictor serves as the foundational component of the Chorus multi-agent immune system, implementing real-time conflict prediction and intervention capabilities for decentralized agent networks. This system leverages Google's Gemini 3 Pro API for game theory analysis to proactively prevent cascading failures in peer-to-peer agent systems without requiring central orchestration.

The design follows a modular architecture that separates concerns between agent simulation, conflict prediction, trust management, and intervention logic. This enables the system to operate as both a standalone conflict predictor and as the core engine for the broader Chorus ecosystem.

## Architecture

The system follows a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI Dashboard Layer                       │
├─────────────────────────────────────────────────────────────┤
│                  Intervention Engine                        │
├─────────────────────────────────────────────────────────────┤
│    Conflict Predictor    │         Trust Manager           │
├─────────────────────────────────────────────────────────────┤
│      Gemini Client       │         Redis Client            │
├─────────────────────────────────────────────────────────────┤
│                   Agent Simulator                           │
└─────────────────────────────────────────────────────────────┘
```

### Key Architectural Principles

1. **Decentralized Agent Model**: Agents operate independently without central coordination
2. **Proactive Intervention**: Conflicts are predicted and prevented before they occur
3. **Game Theory Foundation**: Decision-making based on Nash Equilibrium calculations
4. **Resilient Design**: System continues operating even when individual components fail
5. **Observable Behavior**: All agent interactions and system decisions are logged and trackable

## Components and Interfaces

### Agent Simulator

**Purpose**: Creates a synthetic multi-agent environment for testing and demonstration

**Key Classes**:
- `Agent`: Represents an autonomous agent with independent decision-making
- `ResourceManager`: Manages shared resources that agents compete for
- `AgentNetwork`: Orchestrates the overall simulation environment

**Interfaces**:
```python
class Agent:
    def __init__(self, agent_id: str, initial_trust_score: int = 100)
    def make_resource_request(self, resource_type: str, amount: int) -> ResourceRequest
    def receive_message(self, message: AgentMessage) -> None
    def get_current_intentions(self) -> List[AgentIntention]

class ResourceManager:
    def process_request(self, request: ResourceRequest) -> RequestResult
    def get_resource_status(self, resource_type: str) -> ResourceStatus
    def detect_contention(self) -> List[ContentionEvent]
```

### Gemini Client

**Purpose**: Interfaces with Google's Gemini 3 Pro API for game theory conflict analysis

**Key Classes**:
- `GeminiClient`: Main interface to the Gemini API
- `GameTheoryPromptBuilder`: Constructs prompts for conflict analysis
- `ConflictAnalysisParser`: Parses and validates API responses

**Interfaces**:
```python
class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-3-pro-preview")
    def analyze_conflict_risk(self, agent_intentions: List[AgentIntention]) -> ConflictAnalysis
    def calculate_nash_equilibrium(self, game_state: GameState) -> EquilibriumSolution

class ConflictAnalysis:
    risk_score: float  # 0.0 to 1.0
    affected_agents: List[str]
    predicted_outcome: str
    recommended_actions: List[InterventionAction]
```

### Trust Manager

**Purpose**: Maintains and updates trust scores for all agents using Redis storage

**Key Classes**:
- `TrustScoreManager`: Core trust score operations
- `RedisClient`: Redis database interface
- `TrustPolicy`: Configurable trust score adjustment rules

**Interfaces**:
```python
class TrustScoreManager:
    def get_trust_score(self, agent_id: str) -> int
    def update_trust_score(self, agent_id: str, adjustment: int, reason: str) -> None
    def check_quarantine_threshold(self, agent_id: str) -> bool
    def get_all_trust_scores(self) -> Dict[str, int]
```

### Intervention Engine

**Purpose**: Executes quarantine and other intervention actions based on predictions

**Key Classes**:
- `InterventionEngine`: Main intervention logic
- `QuarantineManager`: Handles agent quarantine operations
- `ActionLogger`: Records all intervention actions

**Interfaces**:
```python
class InterventionEngine:
    def evaluate_intervention_need(self, conflict_analysis: ConflictAnalysis) -> bool
    def execute_quarantine(self, agent_id: str, reason: str) -> QuarantineResult
    def identify_most_aggressive_agent(self, agents: List[str]) -> str
```

## Data Models

### Core Data Structures

```python
@dataclass
class AgentIntention:
    agent_id: str
    resource_type: str
    requested_amount: int
    priority_level: int
    timestamp: datetime

@dataclass
class ConflictAnalysis:
    risk_score: float
    confidence_level: float
    affected_agents: List[str]
    predicted_failure_mode: str
    nash_equilibrium: Optional[EquilibriumSolution]
    timestamp: datetime

@dataclass
class QuarantineAction:
    agent_id: str
    reason: str
    timestamp: datetime
    duration: Optional[int]
    trust_score_before: int
    trust_score_after: int

@dataclass
class AgentMessage:
    sender_id: str
    receiver_id: str
    message_type: str
    content: Dict[str, Any]
    timestamp: datetime
```

### Trust Score Model

```python
class TrustScoreEntry:
    agent_id: str
    current_score: int  # 0-100
    last_updated: datetime
    adjustment_history: List[TrustAdjustment]
    quarantine_count: int
    creation_time: datetime
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After reviewing all properties identified in the prework, several can be consolidated to eliminate redundancy:

- Properties 1.3, 4.3, 5.2, and 6.4 all test logging functionality and can be combined into a comprehensive logging property
- Properties 2.4, 6.1, and 6.2 all test error handling and can be consolidated into a general error resilience property  
- Properties 3.2, 3.5, and 4.5 all test trust score updates and can be combined into a trust score consistency property
- Properties 4.2 and 4.4 test quarantine behavior and can be merged into a single quarantine isolation property

The following properties provide unique validation value and will be implemented:

**Property 1: Agent simulation autonomy**
*For any* agent simulation run, all created agents should operate independently without central coordination, making resource requests at random intervals within the specified range (5-10 agents)
**Validates: Requirements 1.1, 1.2, 1.4, 1.5**

**Property 2: Comprehensive system logging**
*For any* system event (agent actions, quarantine actions, predictions, exceptions), the system should log complete metadata including timestamps, agent IDs, action types, and context information
**Validates: Requirements 1.3, 4.3, 5.2, 6.4**

**Property 3: Gemini API integration correctness**
*For any* set of agent intentions, the Gemini client should format them into valid game theory prompts, use the gemini-3-pro-preview model, and return conflict risk scores between 0.0 and 1.0
**Validates: Requirements 2.1, 2.2, 2.3**

**Property 4: Trust score consistency**
*For any* agent and trust score operation, changes should be immediately persisted to Redis, follow configured adjustment rules, and trigger quarantine consideration when scores fall below 30
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 4.5**

**Property 5: Intervention threshold accuracy**
*For any* conflict analysis with risk score above 0.7, the system should classify it as high-risk, identify the most aggressive agent, and execute appropriate quarantine actions
**Validates: Requirements 2.5, 4.1**

**Property 6: Quarantine isolation effectiveness**
*For any* quarantined agent, it should be prevented from making new resource requests while other agents continue operating normally without disruption
**Validates: Requirements 4.2, 4.4**

**Property 7: System error resilience**
*For any* API failure, Redis connection error, or agent simulation exception, the system should handle errors gracefully, log appropriate information, continue core operations, and alert operators when necessary
**Validates: Requirements 2.4, 6.1, 6.2, 6.3, 6.5**

**Property 8: Real-time CLI updates**
*For any* system state change (predictions, interventions, agent status), the CLI should display updates automatically without user input, showing risk scores, affected agents, and quarantine justifications
**Validates: Requirements 5.3, 5.4, 5.5**

## Error Handling

The system implements comprehensive error handling across all components:

### Gemini API Error Handling
- **Connection Errors**: Retry with exponential backoff up to 3 attempts
- **Rate Limiting**: Implement request queuing with configurable delays
- **Invalid Responses**: Fallback to rule-based conflict detection when API parsing fails
- **Authentication Errors**: Log detailed error information and alert operators

### Redis Error Handling
- **Connection Failures**: Implement connection pooling with automatic reconnection
- **Data Corruption**: Validate data integrity on read operations
- **Memory Limits**: Implement TTL policies for trust score entries
- **Network Timeouts**: Use circuit breaker pattern to prevent cascade failures

### Agent Simulation Error Handling
- **Thread Failures**: Isolate failed agents without stopping the simulation
- **Resource Contention**: Implement fair queuing to prevent starvation
- **Message Corruption**: Validate message format and discard invalid messages
- **Deadlock Prevention**: Implement timeout mechanisms for all agent operations

### System-Level Error Handling
- **Graceful Degradation**: Core functionality continues even when subsystems fail
- **Error Propagation**: Structured error reporting with context preservation
- **Recovery Mechanisms**: Automatic restart of failed components where possible
- **Monitoring Integration**: All errors are logged with appropriate severity levels

## Testing Strategy

The testing strategy employs a dual approach combining unit tests for specific functionality and property-based tests for universal correctness guarantees.

### Unit Testing Approach
- **Component Isolation**: Test individual classes and methods in isolation using mocks
- **Edge Cases**: Verify boundary conditions like empty agent lists, maximum trust scores, and API timeouts
- **Error Conditions**: Test specific error scenarios like invalid API responses and Redis connection failures
- **Integration Points**: Verify correct interaction between components using test doubles

### Property-Based Testing Approach
- **Framework**: Use Hypothesis for Python property-based testing with minimum 100 iterations per property
- **Universal Properties**: Verify correctness properties hold across all valid inputs and system states
- **Generator Strategy**: Create smart generators that produce realistic agent behaviors, resource requests, and system states
- **Shrinking**: Leverage Hypothesis shrinking to find minimal failing examples when properties fail

### Test Organization
- **Test Structure**: Mirror source structure in `tests/` directory
- **Test Naming**: Use descriptive names following `test_{scenario}_{expected_result}` pattern
- **Property Tagging**: Each property-based test tagged with format: `**Feature: agent-conflict-predictor, Property {number}: {property_text}**`
- **Coverage Requirements**: Minimum 80% overall coverage, 95% for critical conflict prediction and trust scoring logic

### Mock Strategy
- **External Dependencies**: Mock Gemini API calls and Redis operations in unit tests
- **Agent Simulation**: Use lightweight test agents for integration testing
- **Time Dependencies**: Mock datetime for deterministic timestamp testing
- **Network Operations**: Mock all external network calls to ensure test reliability

### Integration Testing
- **End-to-End Scenarios**: Test complete workflows from agent simulation through conflict prediction to quarantine
- **Real Dependencies**: Use test instances of Redis and mock Gemini API for integration tests
- **Performance Testing**: Verify system handles expected load of 10 agents with realistic request patterns
- **Failure Scenarios**: Test system behavior under various failure conditions and recovery scenarios