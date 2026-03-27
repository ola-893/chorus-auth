# Readiness Checklist

Use this checklist before a demo, handoff, or review.

## Runtime

- [ ] `backend/venv` exists and dependencies install cleanly
- [ ] `frontend/node_modules` exists and `npm run build` passes
- [ ] `DATABASE_URL` points to a writable location
- [ ] the backend exposes `/ws/dashboard` for live dashboard updates

## Demo State

- [ ] `SEED_DEMO=true`
- [ ] `SEED_ON_STARTUP=true`
- [ ] the mock user can load `/api/me`
- [ ] Gmail and GitHub connected accounts appear in the dashboard
- [ ] `Assistant Agent`, `Builder Agent`, and `Ops Agent` appear with capability grants

## Scenario Validation

- [ ] Gmail draft request completes automatically
- [ ] GitHub issue request pauses for approval
- [ ] approving the GitHub issue resumes execution successfully
- [ ] repeated GitHub merge attempts escalate into quarantine
- [ ] audit events appear for action creation, approval, execution, and quarantine

## Commands To Re-Run

- [ ] `cd frontend && npm test`
- [ ] `cd frontend && npm run build`
- [ ] `cd backend && venv/bin/python -m pytest -o addopts= tests/control_plane/test_demo_smoke.py`
- [ ] `cd backend && venv/bin/python -m src.demo.smoke_runner`
