# Frontend Development Guide

The current frontend is a Vite + React app shell for the auth control plane MVP.

## Main Entry Point

- `frontend/src/App.tsx`

The UI is a single dashboard experience that combines:
- `/login`
- `/overview`
- `/connections`
- `/agents`
- `/approvals`
- `/activity`
- `/demo`

Each page keeps structure and controls in the code while leaving visual treatment intentionally light.

## Page Map

### `/login`

- Sections:
  - product message
  - sign-in state
  - fallback mode notice
- Buttons:
  - `Continue with Auth0`
  - `Use local demo mode`

### `/overview`

- Sections:
  - summary metrics
  - latest protected action spotlight
  - recent pending approvals
  - recent blocked/quarantined actions
  - quick demo controls
- Buttons:
  - `Connect Gmail`
  - `Connect GitHub`
  - `Run Allow Scenario`
  - `Run Approval Scenario`
  - `Run Quarantine Scenario`
  - `Reset Demo`
  - `Open Action Details`
  - `Go To Approvals`

### `/connections`

- Tabs:
  - `Accounts`
  - `Scopes`
  - `Connection Health`
- Buttons:
  - `Connect Gmail`
  - `Connect GitHub`
  - `Reconnect`
  - `Disconnect`
  - `Refresh Connection`
  - `View Vault Reference`

### `/agents`

- Tabs:
  - `Registry`
  - `Capability Grants`
  - `Quarantine`
- Buttons:
  - `Create Agent`
  - `Grant Capability`
  - `Update Constraints`
  - `Disable Agent`
  - `Release Quarantine`
  - `View Action History`

### `/approvals`

- Tabs:
  - `Pending`
  - `Resolved`
- Buttons:
  - `Approve`
  - `Reject`
  - `Open Details`
  - `Open Audit Trail`

### `/activity`

- Tabs:
  - `Timeline`
  - `By Action`
  - `By Agent`
- Buttons:
  - `Filter ALLOW`
  - `Filter APPROVAL`
  - `Filter BLOCK`
  - `Filter QUARANTINE`
  - `Open Details`
  - `Open Provider Result`
  - `Jump To Agent`

### `/demo`

- Sections:
  - guided story steps
  - scenario runner
  - environment readiness
  - live/mock execution status
  - recent demo runs
- Buttons:
  - `Run Full Demo`
  - `Run Allow Step`
  - `Run Approval Step`
  - `Run Quarantine Step`
  - `Reset Workspace`
  - `Copy Demo Script`

## Data Sources

- REST endpoints under `/api` for initial data and state refreshes
- `/ws/dashboard` for live update signals
- Auth0 PKCE redirect handling in the browser when `AUTH_MODE=auth0`

The frontend is intentionally simple: it refetches the key views after mutation events so the UI remains easy to reason about during the demo.

## Local Commands

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

If you want to point the frontend at a hosted API, create `frontend/.env` from `frontend/.env.example` and set `VITE_API_BASE_URL`.

Validation:

```bash
npm test
npm run build
```

## Frontend Conventions

- Keep the interface demo-first and easy to explain.
- Prefer showing capability boundaries, approval state, and reasons over decorative metrics.
- Keep layout and interaction changes separate from visual styling changes when possible.
- Keep empty and degraded states readable; the dashboard should still be useful if realtime updates drop.
