# Chorus API Standards

## REST Design Principles
- Use nouns, not verbs, in endpoint paths (e.g., `/agents`, not `/getAgents`).
- Use HTTP methods explicitly: `GET` (read), `POST` (create), `PUT` (update/replace), `DELETE` (remove).
- Version the API in the URL path: `/v1/agents`.
- Return appropriate HTTP status codes.

## Response Format
All JSON responses follow this envelope format:
```json
{
  "data": { ... }, // The primary response payload
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_abc123",
    "version": "1.0"
  }
}```

Errors use a separate error object:

```json
{
  "error": {
    "code": "CONFLICT_PREDICTION_FAILED",
    "message": "Failed to predict agent conflicts",
    "details": { ... }
  },
  "meta": { ... }
}
```

## Core Endpoints


### Agent Communication

-   `POST /v1/messages/process` - Primary endpoint for processing agent messages through the immune system.

-   `GET /v1/agents/{id}/trust-score` - Retrieve an agent's current trust score.

### System Monitoring

-   `GET /v1/system/health` - Health check for the Chorus service and its dependencies (Gemini API, Datadog, etc.).

-   `GET /v1/dashboard/metrics` - Aggregate metrics for the React dashboard.

## Security & Authentication


-   Internal Agent API: Uses a simple API key header (`X-Agent-API-Key`) validated against an internal store.

-   Dashboard/Admin API: Uses JWT tokens for user authentication.

-   All endpoints must implement rate limiting based on the client or agent identity.

Documentation

-   Use FastAPI's automatic OpenAPI generation.

-   Ensure all endpoint parameters, request bodies, and response models are fully documented in the function docstrings.