# Project Structure

The active repository structure centers on the auth control plane MVP.

## Top-Level Layout

- `backend/`: FastAPI backend, SQLAlchemy models, seeded demo helpers, and tests
- `frontend/`: Vite React dashboard
- `docs/`: current guides plus archived legacy references
- `run_frontend_demo.sh`: seeded full-stack demo launcher
- `run_backend_api.sh`: backend-only control-plane launcher

## Backend Layout

- `src/control_plane_app.py`: current FastAPI entrypoint
- `src/db/`: database models, sessions, and bootstrap helpers
- `src/auth/`, `src/vault/`, `src/connections/`, `src/agents/`
- `src/policy/`, `src/risk/`, `src/enforcement/`
- `src/actions/`, `src/approvals/`, `src/audit/`, `src/providers/`
- `src/demo/`: seeded demo data and smoke runner
- `tests/control_plane/`: targeted control-plane smoke coverage

## Legacy Layout

Older prediction-engine, Kafka, Datadog, and voice-related packages still exist in the repository, but they are not the default runtime path. Treat them as archived experiments unless a doc explicitly says otherwise.
