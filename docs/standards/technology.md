# Chorus Technology Stack

## Mandatory Partner Technologies
### Google Cloud Integration (via Gemini Developer API)
- **Gemini 3 Pro (`gemini-3-pro-preview`)**: Primary conflict prediction engine[citation:10]
- **Authentication**: API key-based (`GEMINI_API_KEY` environment variable)[citation:3]
- **SDK**: Google Gen AI Unified SDK (supports both Gemini API and Vertex AI)[citation:2][citation:5]
- **Hosting**: Google Cloud Run for backend API

### Datadog Integration
- **Datadog APM**: Agent performance monitoring
- **Datadog Logs**: Centralized logging for all agent interactions
- **Datadog Dashboards**: Real-time visualization of system health
- **Datadog Incidents**: Alert management and escalation

### Confluent Cloud
- **Kafka Topics**:
  - `agent-messages-raw`: Raw agent communications
  - `agent-decisions-processed`: Chorus-processed decisions
  - `system-alerts`: Alert stream for Datadog/ElevenLabs

### ElevenLabs
- **Text-to-Speech API**: Voice alerts for critical incidents
- **Real-time Audio Streaming**: <75ms latency for urgent alerts

## Development Stack
### Backend (Python Focus)
```python
# Core dependencies from requirements.txt
google-genai>=1.0.0          # Unified Gen AI SDK[citation:2][citation:5]
confluent-kafka>=2.3         # Confluent integration
datadog-api-client>=2.25     # Datadog metrics
elevenlabs>=1.4              # Voice generation
redis>=5.0                   # Local caching
networkx>=3.2                # Causal graph analysis
pydantic>=2.5                # Data validation
fastapi>=0.104               # API layer
uvicorn>=0.24                # ASGI server