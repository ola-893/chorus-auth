# Testing Standards

The active testing strategy for the auth control plane is intentionally narrow and high-signal.

## Layers

- **Unit tests**: policy rules, risk mapping, capability validation, quarantine thresholds
- **Integration tests**: action lifecycle, approvals, audit trail, websocket updates
- **Smoke tests**: seeded end-to-end demo story

## Required Coverage Areas

- Gmail allow path
- GitHub approval path
- GitHub block-to-quarantine path
- seeded data reset behavior
- frontend rendering of key control-plane states

## Command Standards

- Frontend validation should include `npm test` and `npm run build`.
- Backend smoke validation should include `venv/bin/python -m src.demo.smoke_runner`.
- Targeted pytest runs should prefer the smallest useful scope, especially while the repo still contains broad legacy suites.
