# Chorus Universal Integration Interface & Dashboard Expansion

## 1. Feature: Universal Observation API
**Goal:** Transform Chorus into a plug-and-play safety layer for *any* agent framework (CrewAI, LangGraph, AutoGen).

### Requirements
*   **Ingestion:** A high-performance REST endpoint (`POST /v1/observe`) to receive agent events.
*   **Normalization:** Convert external event schemas into Chorus `AgentMessage` / `AgentIntention`.
*   **Intervention:** A callback/webhook mechanism to notify the external system of "Quarantine" or "Reject" decisions.
*   **Security:** API Key authentication (`X-Chorus-API-Key`).

### API Design

**Endpoint:** `POST /v1/observe`

**Payload:**
```json
{
  "source_system": "crewai-finance-swarm",
  "events": [
    {
      "agent_id": "researcher-gpt4",
      "action_type": "tool_use", // or "message", "reasoning"
      "target": "google_search",
      "content": "What is the stock price of AAPL?",
      "timestamp": "2023-10-27T10:00:00Z",
      "metadata": {
        "priority": "high"
      }
    }
  ]
}
```

**Response:**
```json
{
  "status": "accepted",
  "ingested_count": 1,
  "intervention_required": false // Immediate sync feedback (optional)
}
```

**Endpoint:** `POST /v1/webhooks/register`
Allows external systems to register a URL to receive alerts.

## 2. Feature: Enhanced Visualization (AgentVerse & Universal)
**Goal:** Show the flow of messages from external systems in the Chorus UI.

### Requirements
*   **Real-time Feed:** Stream raw messages from `agent-messages-raw` to the Frontend via WebSockets.
*   **Source Attribution:** Clearly distinguish between "Internal Simulation", "AgentVerse", and "Universal API" sources in the UI.

### Technical Tasks

1.  **Update Bridge:** Modify `kafka_websocket_bridge.py` to subscribe to `agent-messages-raw`.
2.  **Universal Router:** Create `backend/src/api/routes/universal.py` with the `POST /observe` endpoint.
3.  **Kafka Integration:** The Universal Router must push normalized messages to the `agent-messages-raw` Kafka topic (reusing the existing pipeline).
4.  **Frontend Update:** (Out of scope for this CLI session, but backend support provided via WebSocket).

---

## 3. Implementation Plan

### Task 1: Update WebSocket Bridge
Ensure the frontend can "see" what we are monitoring.

### Task 2: Implement Universal API (`universal.py`)
Build the ingestion endpoint using `FastAPI` and `KafkaMessageBus`.

### Task 3: Reference Implementation (Example)
Create `examples/universal_integration/demo_crewai.py` that mocks a CrewAI agent sending data to Chorus.
