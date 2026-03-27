# Chorus Demo Guide

This guide covers the active auth control plane demo path and the supporting smoke checks.

## Recommended Demo Path

### 1. Seeded dashboard demo

```bash
./run_frontend_demo.sh
```

What this does:

- starts the FastAPI auth control plane on port `8000`
- seeds the mock demo workspace on startup
- launches the Vite dashboard on port `5173`
- exposes live updates through `/ws/dashboard`

### 2. Backend smoke runner

```bash
cd backend
venv/bin/python -m src.demo.smoke_runner
```

Use this when you want to verify the narrative quickly without opening the UI.

### 3. Targeted smoke test

```bash
cd backend
venv/bin/python -m pytest -o addopts= tests/control_plane/test_demo_smoke.py
```

## Demo Narrative

The seeded demo is designed for a short sponsor-friendly walkthrough:

1. Show the connected Gmail and GitHub accounts in the dashboard.
2. Open the agent cards and highlight each capability grant.
3. Submit or point to the seeded `Assistant Agent` Gmail draft allow path.
4. Show `Builder Agent` entering the approval queue for a GitHub issue.
5. Approve the request and watch execution finish.
6. Trigger `Ops Agent` twice and show the block-to-quarantine escalation.
7. Finish on the audit timeline and quarantine panel.

## Dashboard Sections

- **Connected Accounts**: Provider scopes and vault references.
- **Agents**: Status, capability grants, and quarantine reasons.
- **Action Studio**: A quick way to submit Gmail and GitHub demo actions.
- **Pending Approvals**: Approve or reject medium-risk actions.
- **Activity Timeline**: Audit trail of action, approval, and quarantine events.
- **Quarantine State**: Immediate view of escalated agents.

## Troubleshooting

- If the frontend cannot load data, confirm the backend is available at `http://localhost:8000`.
- If realtime status shows `offline`, the dashboard will still work with manual refreshes and follow-up API reads.
- If you want a clean demo state, restart with `SEED_ON_STARTUP=true ./run_frontend_demo.sh`.

## Legacy Demos

`./demo_scenarios.sh` still exists for the older immune-system experiments, but it is now a legacy menu and not part of the default sponsor demo path.
