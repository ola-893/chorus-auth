# Authorized To Act Submission Notes

## Submission Positioning

**Chorus** is now framed as a secure authorization and intervention layer for AI agents. Instead of leading with conflict prediction, the demo leads with delegated access, scoped permissions, human approval, and visible enforcement around high-stakes agent actions.

## Why This Fits The Sponsor Prompt

- **Security model**: Agents never receive raw provider credentials. Provider access stays server-side behind the Auth0 and Token Vault adapters.
- **User control**: The dashboard makes connected accounts, agent grants, approval checkpoints, audit events, and quarantine state visible in one place.
- **Technical execution**: Every action goes through deterministic policy, contextual risk evaluation, and an explicit enforcement decision before any provider call happens.
- **Insight value**: The product shows how multi-agent systems can keep least privilege and human control even when multiple agents act on a user’s behalf.

## Demo Story

The seeded MVP uses one user, two connected providers, and three specialized agents:

1. `Assistant Agent` creates a Gmail draft automatically for an approved domain.
2. `Builder Agent` requests a GitHub issue and pauses for approval.
3. `Ops Agent` attempts a GitHub pull request merge, is blocked, then quarantined on a repeat attempt.

That sequence shows `ALLOW`, `REQUIRE_APPROVAL`, `BLOCK`, and `QUARANTINE` decisions in under a minute.

## Sponsor-Relevant Architecture

- **Auth**: Mock-first Auth0-compatible adapter with a stable interface for real tenant wiring.
- **Vault**: Mock-first Token Vault adapter that mediates provider access and keeps tokens off-agent.
- **Providers**: Gmail and GitHub execution adapters with normalized results.
- **Policy and risk**: Deterministic capability checks backed by Gemini explanations for contextual risk.
- **Audit**: Append-only event trail plus live dashboard updates over `/ws/dashboard`.

## How To Run The Submission

```bash
./run_frontend_demo.sh
```

Optional smoke verification:

```bash
cd backend
venv/bin/python -m src.demo.smoke_runner
```

## Demo Talking Points

- Least privilege is visible at the agent level, not buried in backend code.
- Approval is treated as a first-class lifecycle state, not a manual side channel.
- Repeated violations escalate automatically into quarantine.
- The MVP remains usable in mock mode, but the Auth0 and Token Vault seams are already explicit.
