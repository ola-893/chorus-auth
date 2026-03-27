# Backend Development Guide

The current backend is the Chorus auth control plane. It is implemented in FastAPI and organized around bounded contexts instead of one monolithic pipeline.

## Main Entry Point

- `backend/src/control_plane_app.py`

This app wires:

- REST routes under `/api`
- websocket updates under `/ws/dashboard`
- schema creation and reference seeding on startup
- optional demo seeding for the mock MVP

## Core Packages

- `auth`: current-user resolution
- `vault`: provider access abstraction
- `connections`: connected account persistence
- `agents`: agent registry and capability grants
- `policy`: deterministic allow and deny checks
- `risk`: rule-based risk with optional Gemini explanation
- `enforcement`: final decision mapping
- `actions`: action request lifecycle
- `approvals`: approval queue and decision handling
- `audit`: append-only event log
- `providers`: Gmail and GitHub execution adapters
- `demo`: seeded data and smoke runner

## Local Commands

```bash
cd backend
source venv/bin/activate
uvicorn src.control_plane_app:create_app --factory --reload
```

Useful checks:

```bash
venv/bin/python -m src.demo.smoke_runner
venv/bin/python -m pytest -o addopts= tests/control_plane/test_demo_smoke.py
```

## Request Flow

1. Resolve the current user.
2. Look up the target agent and capability grant.
3. Validate provider connection and scope constraints.
4. Assess risk.
5. Map the result to allow, approval, block, or quarantine.
6. Execute through the provider adapter only when permitted.
7. Record audit events and publish dashboard updates.

## Development Notes

- Keep mock and live adapter seams stable. The mock path is the demo default.
- Prefer deterministic policy decisions even when Gemini is unavailable.
- Treat direct token access as a backend-only concern.
- Keep commit boundaries aligned with a single backend idea whenever possible.
