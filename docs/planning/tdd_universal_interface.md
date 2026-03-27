# Technical Design Document (TDD) - Chorus Universal Interface
Version: 1.0
Audience: Software Architects, Engineers
Supersedes: N/A

## 1. System Context & Architecture Evolution

### 1.1 Current Architecture (Pre-Universal Interface)
```
[Agent Simulator] -> [Kafka] -> [Chorus Core] -> [Dashboard]
                          |-> [Gemini Predictor]
                          |-> [Redis Trust Store]
```
A monolithic but functional system tightly coupled to a specific simulation.

### 1.2 Target Architecture (Universal Interface v1)
```
                    ┌─────────────────────────────────────┐
                    │         Chorus Core Service         │
                    │  (Prediction, Trust, Causal Graph)  │
                    └────────────────┬──────────────┬─────┘
                                     │              │
                            ┌────────▼────┐  ┌─────▼──────────┐
                            │ Universal   │  │ Intervention   │
                            │ Observer API │  │ Gateway &      │
                            │ (REST/HTTPS) │  │ Webhook Engine │
                            │ (FastAPI)    │  │ (Redis Stream) │
                            └──────┬───────┘  └────────┬───────┘
                                   │                   │
        ┌──────────────────────────┼───────────────────┼──────────────────────────┐
        │                          │                   │                          │
┌───────▼──────────┐      ┌───────▼──────────┐ ┌──────▼──────────┐      ┌────────▼────────┐
│ AgentVerse       │      │ LangGraph Adapter│ │ Custom REST     │      │ Network A       │
│ Adapter          │      │ (Future)         │ │ Adapter (Future)│      │ Webhook Endpoint│
│ (Polling Mode)   │      │                  │ │                 │      │                 │
└──────────────────┘      └──────────────────┘ └──────────────────┘      └─────────────────┘
        |                          |                   |                          ^
        |                          |                   |                          |
┌───────▼──────────┐      ┌───────▼──────────┐ ┌───────▼──────────┐      ┌───────────────┐
│ AgentVerse       │      │ LangGraph        │ │ Any Network with │      │ Network A     │
│ Network          │      │ Network          │ │ REST API         │      │ Internal      │
│                  │      │                  │ │                  │      │ Control Plane │
└──────────────────┘      └──────────────────┘ └──────────────────┘      └───────────────┘
```
Chorus Core becomes a central service. Networks connect via **Adapters** (push or pull) or directly via the **Observer API**.

## 2. Component Deep Dive

### 2.1 Universal Observer API
**Technology:** FastAPI (leveraging existing codebase).
**Endpoint:** `POST /v1/observe`

**Key Design Decisions:**
- **Async Processing:** Immediate 202 response to caller; event processing is queued (Kafka) to guarantee scalability.
- **Schema Validation:** Strict Pydantic models reject malformed data at the edge.
- **Idempotency Key:** Required header to prevent duplicate processing from retries.

```python
# Simplified Request Schema
class ChorusObservation(BaseModel):
    network_id: str = Field(..., description="Registered network identifier")
    event_id: str = Field(..., description="Unique idempotency key for this event")
    timestamp: datetime
    agent_id: str
    event_type: Literal["message_sent", "resource_requested", "goal_declared"]
    payload: dict = Field(default_factory=dict)
```

### 2.2 Adapter System (`src/integrations/`)
**Pattern:** Strategy Pattern via Abstract Base Class.

**Directory Structure:**
```
src/integrations/
├── __init__.py
├── base.py              # BaseNetworkAdapter ABC
├── agentverse/          # Reference implementation
│   ├── __init__.py
│   ├── adapter.py       # AgentVerseAdapter
│   └── client.py        # Wraps AgentVerse API
├── langgraph/           # Future
└── generic_rest/        # Future (for any HTTP-push network)
```

**Base Adapter Contract:**
```python
class BaseNetworkAdapter(ABC):
    def __init__(self, config: NetworkConfig, chorus_client: ChorusObserverClient):
        self.config = config
        self.chorus_client = chorus_client

    @abstractmethod
    async def start(self):
        """Start polling or subscribing to the network's event stream."""
        pass

    @abstractmethod
    async def stop(self):
        """Gracefully shut down the adapter."""
        pass

    @abstractmethod
    async def execute_intervention(self, intervention: Intervention):
        """Execute a Chorus directive on the network."""
        pass
```

### 2.3 Intervention Gateway
- **Flow:** InterventionEngine -> Intervention Gateway -> Network Webhook
- **Resilience:** Uses a persistent queue (Redis Streams) to store pending interventions. Guarantees at-least-once delivery.
- **Security:** Webhook endpoints must be pre-registered. Supports HMAC signatures for payload verification.

### 2.4 Agent Identity & Trust Store
**Schema Extension:** The existing Redis trust store is augmented.
```json
# Key: chorus:agent:trust:{agent_global_id}
{
  "score": 85,
  "history": [
    {"network": "agentverse", "event": "conflict", "delta": -10, "timestamp": "..."}
  ],
  "metadata": {"original_networks": ["agentverse", "network_b"]}
}
```

## 3. Data Flow for Key Scenarios

**Scenario A: Network Pushes an Event (Simple Integration)**
1. Network's backend calls `POST https://api.chorus.dev/v1/observe`.
2. Observer API validates, authenticates, publishes to `raw-events` Kafka topic.
3. Existing Chorus Core processors consume, predict, update trust scores.
4. If intervention needed, **Intervention Gateway** queues command for that network's webhook.
5. Network receives POST to its webhook and acts (e.g., pauses an agent).

**Scenario B: Adapter Polls for Events (Legacy or Pull-based Network)**
1. `AgentVerseAdapter.start()` polls the AgentVerse mailbox every 30s.
2. Fetches new `StoredEnvelope` messages, transforms to `ChorusObservation`.
3. Adapter uses the internal `ChorusObserverClient` (same library as external networks) to push events via the same Observer API.
4. Flow continues identically from Step 2 of Scenario A.

## 4. Integration with Existing Hackathon Codebase
Your current system is not thrown away; it is refactored and generalized.
- `examples/llm_fleet_simulator/` becomes the first and most advanced adapter (`LocalSimulationAdapter`).
- Your existing Kafka topics remain the internal message bus.
- The Gemini Predictor and Redis Trust Manager require zero changes.
- The Dashboard gets a new network filter and visualization layer.

**Immediate Hackathon Actionable Step:**
Create the `base.py` ABC and refactor your AgentVerse polling logic into `AgentVerseAdapter`. This demonstrates the architectural shift within your submission.

## 5. Deployment & Configuration
- **Chorus Core Service:** Deployable as a container (Docker) on Google Cloud Run.
- **Adapters:** Can be deployed as sidecar containers alongside network services or as independent microservices.
- **Configuration:** Each adapter is configured via environment variables or a config file, specifying the network's credentials and the Chorus Core endpoint.

## 6. Security Considerations
- **API Key Management:** Use Google Cloud Secret Manager for production. For hackathon, environment variables suffice.
- **Webhook Security:** Require networks to provide a shared secret for HMAC signing of intervention payloads.
- **Data Isolation:** All events and trust scores are tagged with `network_id`. Adapters can only query/act on data for their network.
