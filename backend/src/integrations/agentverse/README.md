# AgentVerse Integration

This module integrates Chorus with the AgentVerse marketplace to provide "Decentralized Observability".

## Features
*   **Mailbox Polling:** Periodically fetches messages from a hosted AgentVerse agent.
*   **Conflict Prediction:** Feeds external messages into the Chorus Prediction Engine via Kafka (`agent-messages-raw`).
*   **Identity Resolution:** (Planned) Resolves AgentVerse addresses to human-readable names via Almanac.

## Configuration

To enable this integration, set the following environment variables in `backend/.env`:

```bash
# Required
AGENTVERSE_API_KEY=your_agentverse_api_key
AGENTVERSE_MONITORED_ADDRESS=agent1q...  # The address of YOUR hosted agent to monitor

# Optional
AGENTVERSE_POLL_INTERVAL=10.0  # Seconds between polls (default: 10.0)
```

## Architecture

1.  **Poller (`poller.py`):** Runs as a background thread in the backend.
2.  **Client (`client.py`):** Wraps the AgentVerse REST API.
3.  **Adapter (`adapter.py`):** Converts AgentVerse `StoredEnvelope` -> Chorus `AgentMessage`.
4.  **Deduplication:** Uses Redis key `chorus:av:msg:{uuid}` to prevent reprocessing messages.
