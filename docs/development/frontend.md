# Frontend Development Guide

The current frontend is a Vite + React dashboard for the auth control plane MVP.

## Main Entry Point

- `frontend/src/App.tsx`

The UI is a single dashboard experience that combines:

- connected accounts
- agent cards and capability grants
- an action submission studio
- pending approvals
- activity timeline
- quarantine state

## Data Sources

- REST endpoints under `/api` for initial data and state refreshes
- `/ws/dashboard` for live update signals

The frontend is intentionally simple: it refetches the key views after mutation events so the UI remains easy to reason about during the demo.

## Local Commands

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

Validation:

```bash
npm test
npm run build
```

## Frontend Conventions

- Keep the interface demo-first and easy to explain.
- Prefer showing capability boundaries, approval state, and reasons over decorative metrics.
- Use the existing warm visual direction rather than reintroducing the old cyberpunk treatment.
- Keep empty and degraded states readable; the dashboard should still be useful if realtime updates drop.
