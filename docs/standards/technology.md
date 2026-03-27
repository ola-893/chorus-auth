# Technology Stack

## Active MVP Stack

### Backend

- `FastAPI`: API and websocket surface
- `SQLAlchemy 2.x`: relational data model and persistence
- `Alembic`: schema migrations
- `Pydantic` and `pydantic-settings`: schemas and configuration

### Frontend

- `React 18`
- `Vite`
- `TypeScript`
- `Vitest` and Testing Library

### Runtime Services

- `SQLite`: default local database
- `Redis`: optional live fanout and ephemeral coordination
- `Gemini`: optional contextual risk explanation

### Integration Seams

- Auth0-compatible auth adapter
- Token Vault-compatible access adapter
- Gmail provider adapter
- GitHub provider adapter

## Out Of The Default Path

Kafka, Datadog, and ElevenLabs remain in the repository only as historical or experimental integrations. They are not part of the active auth control plane MVP stack.
