# Chorus Auth Control Plane

**A secure control plane for delegated AI agent actions with scoped capabilities, approval workflows, and auditable execution.**

Chorus now centers on one clear product story: users connect provider accounts, grant narrow capabilities to specialized agents, and route every agent action through policy, risk, approval, and audit controls before execution. The default MVP runs in mock mode with Gmail and GitHub adapters, SQLite persistence, Redis for live fanout, and a fresh React dashboard.

## What The Demo Shows

The seeded demo follows three agents:

- `Assistant Agent` auto-creates a Gmail draft for an approved domain.
- `Builder Agent` requests a GitHub issue and pauses in a human approval queue.
- `Ops Agent` attempts a sensitive pull request merge, gets blocked, and is quarantined on repeat.

That flow demonstrates:

- delegated access through Auth0 and Token Vault adapters
- least-privilege capability grants per agent
- deterministic policy plus Gemini-backed risk explanations
- approval-aware execution and immutable audit history
- quarantine enforcement for repeated violations

## Quick Start

### Full dashboard demo

```bash
./run_frontend_demo.sh
```

This starts the FastAPI control plane, seeds the mock demo workspace, and launches the Vite dashboard.

### Smoke-check the seeded story

```bash
cd backend
venv/bin/python -m src.demo.smoke_runner
```

Expected outcomes:

- `allow_status=completed`
- `approval_status=pending_approval`
- `approved_queue_status=approved`
- `second_block_status=quarantined`

## Core Architecture

- **Frontend**: React dashboard for connected accounts, agent permissions, pending approvals, activity timeline, and quarantine state.
- **Backend**: FastAPI control plane with bounded contexts for `auth`, `vault`, `connections`, `agents`, `policy`, `risk`, `enforcement`, `actions`, `approvals`, `audit`, and `providers`.
- **Storage**: SQLite for persisted state and Redis for optional live fanout and ephemeral coordination.
- **Execution Model**: Agents request capabilities, not raw tokens. The backend evaluates policy and risk, retrieves provider access through the vault adapter, executes the action, and records the full trail.

## Documentation

### Start here

- [System Overview](docs/architecture/system_overview.md)
- [Demo Guide](docs/guides/demos.md)
- [Hackathon Submission Notes](docs/guides/hackathon.md)
- [Product Overview](docs/planning/product_overview.md)

### Planning specs

- [Auth Control Plane Requirements](docs/planning/specs/auth-control-plane/requirements.md)
- [Auth Control Plane Design](docs/planning/specs/auth-control-plane/design.md)
- [Auth Control Plane Tasks](docs/planning/specs/auth-control-plane/tasks.md)

### Supporting references

- [Deployment Guide](docs/deployment/guide.md)
- [Environment Variables](docs/deployment/environment_variables.md)
- [Development Backend Guide](docs/development/backend.md)
- [Development Frontend Guide](docs/development/frontend.md)
- [API Standards](docs/standards/api.md)
- [Project Structure](docs/standards/structure.md)
- [Testing Standards](docs/standards/testing.md)

## Runtime Defaults

- `USE_NEW_ACTION_PIPELINE=true`
- `USE_LEGACY_PIPELINE=false`
- `AUTH_MODE=mock`
- `VAULT_MODE=mock`
- `PROVIDER_MODE=mock`
- `SEED_DEMO=true`

## Legacy Note

The original immune-system, Kafka, Datadog, and voice-alert experiments remain in the repository for reference, but they are no longer part of the default demo path. Treat scripts and docs that still describe the old prediction platform as legacy unless they explicitly mention the auth control plane.

Archived top-level reference docs are called out directly in places like:

- [Legacy Integration Design](docs/architecture/integration_design.md)
- [Legacy Kafka Implementation](docs/architecture/kafka_implementation.md)
- [Legacy CLI Dashboard](docs/development/cli_dashboard.md)
