# Design Document - Real-Time Data Flow

## Overview

The Real-Time Data Flow phase transforms the Chorus system from a synchronous, direct-call architecture to an event-driven, streaming architecture using Confluent Kafka as the central message bus. This design enables horizontal scalability, fault tolerance, and sophisticated real-time analytics while maintaining the existing conflict prediction and trust management capabilities.

The system will process agent communications through streaming pipelines, provide real-time causal graph visualization of agent interactions, and implement advanced pattern detection for emergent behaviors. This architecture supports the system's evolution from a prototype to a production-ready platform capable of handling thousands of concurrent agents.

## Architecture

### Event-Driven Core Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Agent Fleet   │───▶│  Kafka Message   │───▶│ Stream Processor│
│                 │    │      Bus         │    │   Pipeline      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │                          │
                              ▼                          ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Dashboard UI   │◀───│  WebSocket       │◀───│ Event Analytics │
│  (Causal Graph) │    │   Gateway        │    │    Engine       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Kafka Topic Architecture

- **agent-messages-raw**: Raw agent communications with full message context
- **agent-decisions-processed**: Enriched messages with conflict analysis results
- **system-alerts**: Critical alerts for quarantine actions and emergent patterns
- **causal-graph-updates**: Real-time graph topology changes for visualization
- **analytics-metrics**: Aggregated system performance and behavior metrics

### Stream Processing Flow

1. **Ingestion Layer**: Agents produce messages to agent-messages-raw topic
2. **Processing Layer**: Chorus consumers analyze messages through existing prediction engine
3. **Enrichment Layer**: Results are enriched with metadata and produced to processed topics
4. **Analytics Layer**: Stream processors calculate real-time metrics and detect patterns
5. **Visualization Layer**: WebSocket gateway streams updates to dashboard components

## Components and Interfaces

### Kafka Integration Layer

**KafkaMessageBus**
- Manages Confluent Cloud connections using SASL_SSL security protocol
- Implements producer/consumer patterns with proper serialization
- Handles connection failures, retries, and dead letter queue routing
- Provides message ordering guarantees within agent-specific partitions

**Confluent Cloud Configuration Requirements:**
- Security Protocol: SASL_SSL (encrypted connections required)
- SASL Mechanism: PLAIN (standard auth for Confluent Cloud)
- Bootstrap Servers: Cluster-specific URL (e.g., pkc-xxxxx.us-east-1.aws.confluent.cloud:9092)
- Authentication: API Key (username) and API Secret (password)
- Topic Management: Programmatic creation with proper retention and partitioning strategies

**StreamProcessor**
- Consumes from agent-messages-raw and processes through existing prediction pipeline
- Produces enriched results to agent-decisions-processed topic
- Implements error handling and message replay capabilities
- Maintains processing state for exactly-once delivery semantics

### Causal Graph Engine

**GraphTopologyManager**
- Maintains real-time graph representation of agent interactions
- Detects routing loops, resource hoarding, and communication cascades
- Calculates graph metrics including centrality, clustering, and path analysis
- Produces topology updates to causal-graph-updates topic

**VisualizationEngine**
- Renders interactive D3.js-based causal graph in dashboard
- Handles real-time updates through WebSocket connections
- Implements filtering, zooming, and node selection capabilities
- Provides animation for temporal evolution of relationships

### Stream Analytics Engine

**PatternDetector**
- Analyzes message streams for complex emergent behaviors
- Implements algorithms for Byzantine behavior detection
- Calculates statistical anomalies in communication patterns
- Generates alerts for routing loops and resource hoarding

**MetricsAggregator**
- Computes real-time system performance metrics
- Tracks throughput, latency, error rates, and trust score distributions
- Provides temporal queries for historical analysis
- Supports predictive analytics based on streaming data trends

## Data Models

### Kafka Message Schemas

**AgentMessage (agent-messages-raw)**
```python
@dataclass
class AgentMessage:
    agent_id: str
    timestamp: datetime
    message_type: str  # 'request', 'response', 'broadcast'
    content: Dict[str, Any]
    target_agents: List[str]
    correlation_id: str
    metadata: Dict[str, Any]
```

**ProcessedDecision (agent-decisions-processed)**
```python
@dataclass
class ProcessedDecision:
    original_message: AgentMessage
    conflict_analysis: ConflictAnalysis
    trust_impact: TrustScoreUpdate
    intervention_action: Optional[InterventionAction]
    processing_metadata: ProcessingMetadata
    causal_relationships: List[CausalEdge]
```

**CausalGraphUpdate (causal-graph-updates)**
```python
@dataclass
class CausalGraphUpdate:
    update_type: str  # 'node_added', 'edge_created', 'node_quarantined'
    affected_nodes: List[str]
    edge_changes: List[CausalEdge]
    graph_metrics: GraphMetrics
    timestamp: datetime
```

### Graph Data Structures

**CausalEdge**
```python
@dataclass
class CausalEdge:
    source_agent: str
    target_agent: str
    relationship_type: str  # 'request', 'dependency', 'conflict'
    strength: float  # 0.0 to 1.0
    created_at: datetime
    last_updated: datetime
```

**GraphMetrics**
```python
@dataclass
class GraphMetrics:
    node_count: int
    edge_count: int
    clustering_coefficient: float
    average_path_length: float
    detected_loops: List[List[str]]
    isolated_nodes: List[str]
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After reviewing all testable properties from the prework analysis, several redundancies were identified:
- Properties for message serialization and processing can be combined into comprehensive message flow properties
- Error handling properties for Kafka operations and processing can be consolidated
- Graph update properties can be unified to cover all interaction types
- Pattern detection properties share common verification approaches

The following properties represent the unique, non-redundant correctness guarantees:

**Property 1: Message serialization round trip**
*For any* agent message, producing it to Kafka and consuming it back should yield an equivalent message with proper serialization
**Validates: Requirements 1.2**

**Property 2: Kafka error handling with retry and DLQ**
*For any* Kafka operation failure, the system should implement retry logic and route persistent failures to dead letter queues
**Validates: Requirements 1.3**

**Property 3: Message buffering and replay on reconnection**
*For any* period of Kafka connectivity loss, messages should be buffered locally and replayed in order when connection is restored
**Validates: Requirements 1.5**

**Property 4: Stream processing pipeline integration**
*For any* message on agent-messages-raw topic, it should be processed through the prediction pipeline and produce results on agent-decisions-processed topic
**Validates: Requirements 2.1, 2.2**

**Property 5: Processing error routing**
*For any* processing error, failed messages should be routed to error topics with proper error metadata
**Validates: Requirements 2.3**

**Property 6: Agent-specific message ordering**
*For any* sequence of messages from the same agent, they should maintain their original order within agent-specific partitions
**Validates: Requirements 2.4**

**Property 7: Real-time graph updates**
*For any* agent interaction, the causal graph should update to reflect new nodes and relationship edges
**Validates: Requirements 3.1**

**Property 8: Routing loop detection and highlighting**
*For any* circular dependency pattern in agent communications, the system should detect and highlight the routing loop
**Validates: Requirements 3.2**

**Property 9: Quarantine status visualization**
*For any* quarantined agent, the graph should show isolation status and affected connection paths
**Validates: Requirements 3.3**

**Property 10: Real-time dashboard updates**
*For any* event streaming through Kafka, dashboard metrics should update in real-time without requiring polling
**Validates: Requirements 4.2**

**Property 11: Multi-user synchronization**
*For any* dashboard update, all connected users should receive synchronized real-time updates
**Validates: Requirements 4.5**

**Property 12: Advanced pattern detection**
*For any* routing loop, resource hoarding, communication cascade, or Byzantine behavior pattern, the system should detect and generate appropriate alerts
**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**

**Property 13: Event sourcing persistence**
*For any* processed event, it should be maintained in Kafka topics with configurable retention for complete audit trails
**Validates: Requirements 6.1, 6.4**

**Property 14: Event replay from any time point**
*For any* historical timestamp, the system should be able to replay events from that point to reconstruct system state
**Validates: Requirements 6.2**

**Property 15: Historical event querying**
*For any* query criteria (agent, time range, event type), the system should return matching historical events
**Validates: Requirements 6.3, 6.5**

**Property 16: Real-time metrics calculation**
*For any* message stream processing, the system should calculate accurate real-time metrics including throughput, latency, and error rates
**Validates: Requirements 7.1**

**Property 17: Statistical anomaly detection**
*For any* significant change in agent behavior patterns, the system should detect and flag statistical anomalies
**Validates: Requirements 7.2**

**Property 18: Aggregated statistics generation**
*For any* system data, the system should provide accurate aggregated statistics on conflict rates, intervention effectiveness, and trust score distributions
**Validates: Requirements 7.4**

## Error Handling

### Kafka Connection Failures
- **Connection Loss**: Implement exponential backoff retry with circuit breaker pattern
- **Topic Creation Failures**: Validate topic configurations and provide clear error messages
- **Authentication Errors**: Validate Confluent Cloud API key/secret credentials and SASL_SSL configuration
- **Bootstrap Server Errors**: Handle incorrect cluster URLs and network connectivity issues
- **Partition Failures**: Handle partition reassignment and consumer rebalancing gracefully

### Stream Processing Errors
- **Deserialization Failures**: Route malformed messages to dead letter queue with error metadata
- **Processing Timeouts**: Implement configurable timeouts with retry mechanisms
- **Memory Pressure**: Implement backpressure handling to prevent out-of-memory conditions
- **Duplicate Processing**: Use idempotency keys to handle exactly-once processing semantics

### Causal Graph Errors
- **Graph Complexity Overflow**: Implement node and edge limits with graceful degradation
- **Circular Reference Detection**: Handle infinite loops in graph traversal algorithms
- **Visualization Rendering Failures**: Provide fallback text-based representations
- **WebSocket Connection Drops**: Implement automatic reconnection with state synchronization

### Analytics Engine Errors
- **Pattern Detection False Positives**: Implement confidence thresholds and human verification workflows
- **Metrics Calculation Overflow**: Handle large number processing with appropriate data types
- **Historical Query Timeouts**: Implement query optimization and result pagination
- **Anomaly Detection Sensitivity**: Provide configurable sensitivity parameters for different environments

## Testing Strategy

### Dual Testing Approach

The system requires both unit testing and property-based testing to ensure comprehensive coverage:

**Unit Testing Focus:**
- Kafka client connection and topic management
- Message serialization/deserialization edge cases
- Graph algorithm correctness for specific scenarios
- WebSocket connection handling and error recovery
- Dashboard component integration points

**Property-Based Testing Focus:**
- Message flow properties across all Kafka operations (Properties 1-6)
- Graph update and visualization properties (Properties 7-11)
- Pattern detection across diverse agent behaviors (Property 12)
- Event sourcing and replay consistency (Properties 13-15)
- Analytics and metrics accuracy (Properties 16-18)

**Property-Based Testing Configuration:**
- Use **Hypothesis** for Python property-based testing
- Configure each property test to run a minimum of **100 iterations**
- Each property test must include a comment with the format: **Feature: real-time-data-flow, Property {number}: {property_text}**
- Properties must validate universal behaviors across all valid inputs, not specific examples

**Integration Testing Requirements:**
- Test actual Confluent Kafka integration with test topics
- Validate WebSocket real-time updates with multiple concurrent connections
- Test causal graph rendering with D3.js under various data loads
- Verify end-to-end message flow from agent communication to dashboard visualization

**Performance Testing Considerations:**
- Message throughput testing with varying load patterns
- Graph rendering performance with large numbers of nodes and edges
- WebSocket scalability with multiple concurrent dashboard users
- Stream processing latency under different message volumes