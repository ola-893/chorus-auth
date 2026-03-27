# Auth Control Plane Implementation Plan

## Completed MVP Tasks

- [x] 1. Add specification documents and planning links
  - Create `requirements.md`, `design.md`, and `tasks.md` for the auth control plane refactor
  - Add cross-links from top-level planning and README sections
  - _Requirements: 11.3, 12.3_

- [x] 2. Simplify runtime defaults
  - Remove Kafka, Datadog, and ElevenLabs from the default local and demo path
  - Add config flags for the new control plane and legacy pipeline behavior
  - Update compose and launch scripts to target the new MVP path by default
  - _Requirements: 11.3, 12.1, 12.2, 12.3_

- [x] 3. Add persistence and backend scaffolding
  - Introduce SQLAlchemy and Alembic
  - Add new bounded-context packages under `backend/src`
  - Add SQLite-backed session management and base models
  - _Requirements: 12.4_

- [x] 4. Implement auth and vault foundations
  - Add mock and live adapter interfaces for Auth0 and Token Vault
  - Expose `GET /api/me`
  - Add connected-account storage and API contracts
  - _Requirements: 1.1, 1.2, 2.1, 2.2, 2.3, 2.4_

- [x] 5. Implement agent registry and capability grants
  - Add agent CRUD
  - Add capabilities and agent capability grants
  - Surface granted capabilities in the API
  - _Requirements: 3.1, 3.2, 4.1, 4.2, 4.4_

- [x] 6. Implement policy, risk, and enforcement
  - Add deterministic policy validation
  - Add deterministic risk classification with optional Gemini augmentation
  - Map policy and risk outputs into final enforcement decisions
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 7.1, 7.2, 7.3, 7.4_

- [x] 7. Implement the action lifecycle and audit trail
  - Add action request persistence and list/detail APIs
  - Add provider adapters for Gmail and GitHub
  - Add append-only audit events and timeline queries
  - _Requirements: 5.1, 5.2, 5.3, 9.1, 9.2, 9.3, 9.4_

- [x] 8. Implement approval workflow and quarantine enforcement
  - Add pending approval listing and decision endpoints
  - Resume approved actions and close rejected ones
  - Add repeated-violation escalation into quarantine
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 10.1, 10.2, 10.3, 10.4_

- [x] 9. Build the frontend dashboard
  - Bootstrap a Vite React app in `frontend/`
  - Add views for connected accounts, agents, approvals, audit timeline, and quarantine state
  - Add WebSocket-driven realtime updates
  - _Requirements: 2.1, 3.3, 3.4, 4.4, 8.2, 9.3, 9.4, 10.4_

- [x] 10. Add seeded demo data and smoke coverage
  - Seed one user, two connections, and three agents
  - Add a smoke path covering allow, approval, and quarantine scenarios
  - Verify `run_frontend_demo.sh` uses the seeded MVP path
  - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [x] 11. Rewrite the product story and retire legacy defaults
  - Rewrite README, hackathon docs, and planning docs to the new authorization narrative
  - Keep legacy code optional but remove it from the default docs and runtime path
  - _Requirements: 11.3, 12.2, 12.3_

## Post-MVP Continuation Queue

- [ ] 12. Harden live Auth0 and Token Vault integration
  - Replace header-based `auth0` placeholder behavior with real JWT validation
  - Add production-ready Token Vault credential exchange and error handling
  - Add integration coverage for live-mode auth and vault adapters

- [ ] 13. Add explicit step-up authentication states
  - Introduce `REQUIRE_STEP_UP_AUTH` as a first-class enforcement path
  - Add backend state transitions and dashboard handling for step-up challenges
  - Extend the seeded demo with one step-up example if it stays explainable

- [ ] 14. Expand provider execution beyond mock mode
  - Add live Gmail and GitHub execution strategies behind the current provider interfaces
  - Add safer payload validation and provider-specific result normalization
  - Add contract tests for mock and live provider adapters

- [ ] 15. Deepen operational coverage
  - Add broader backend integration tests around websocket fanout and degraded modes
  - Add more frontend interaction tests for approvals, quarantine, and error states
  - Document a release checklist for demo mode versus live mode
