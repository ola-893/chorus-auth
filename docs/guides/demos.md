# Chorus Demo Guide

This guide covers the active auth control plane demo path and the supporting smoke checks.

## Recommended Demo Path

### 1. Seeded dashboard demo

```bash
./run_frontend_demo.sh
```

What this does:

- starts the FastAPI auth control plane on port `8000`
- waits for `/health` before continuing
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
2. Open `/agents` and highlight each capability grant.
3. Go to `/overview` or `/demo` and run the allow scenario.
4. Run the approval scenario, then open `/approvals` and approve it.
5. Run the quarantine scenario and show the agent state update.
6. Finish on `/activity` with the detail drawer open on the protected action.

## Dashboard Pages

- **`/overview`**: summary cards, spotlight action, pending approvals, and quick scenario buttons.
- **`/connections`**: provider cards, scopes, health, and vault references.
- **`/agents`**: registry, capability grant editor, quarantine controls, and agent history jumps.
- **`/approvals`**: pending/resolved approval queues and decision actions.
- **`/activity`**: timeline, grouped action views, filters, provider-result jumps, and the detail drawer.
- **`/demo`**: scripted scenario controls, environment readiness, and reset helpers.

## Troubleshooting

- If the frontend cannot load data, confirm the backend is available at `http://localhost:8000`.
- If the frontend is hosted separately, confirm `VITE_API_BASE_URL` and `CORS_ALLOWED_ORIGINS` point at each other correctly.
- If realtime status shows `offline`, the dashboard will still work with manual refreshes and follow-up API reads.
- If you want a clean demo state, restart with `SEED_ON_STARTUP=true ./run_frontend_demo.sh`.
