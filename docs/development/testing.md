# Development Testing Guide

Use these commands while working on the auth control plane MVP.

## Frontend

```bash
cd frontend
npm test
npm run build
```

## Backend

```bash
cd backend
venv/bin/python -m pytest -o addopts= tests/control_plane/test_demo_smoke.py
venv/bin/python -m src.demo.smoke_runner
```

## What The Smoke Path Covers

- seeded demo user and connected accounts
- agent capability grants
- allowed Gmail draft execution
- approval-required GitHub issue flow
- blocked then quarantined GitHub merge flow
- audit event creation

## Testing Advice

- Use the smoke runner when you want a fast confidence check against the full seeded story.
- Use targeted pytest files with `-o addopts=` when the repo-wide legacy test defaults are too broad for the control-plane slice.
- Keep frontend tests focused on visible control-plane states rather than implementation details.
