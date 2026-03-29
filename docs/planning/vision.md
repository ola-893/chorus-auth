# Chorus — Product Vision Notes

> Notes from backend dev discussion. For frontend reference.

## The Shift

Chorus is moving from a "predict agent risk" system to a "control what agents are allowed to do" system.

- Old: Chorus watches agents and flags potentially dangerous behavior
- New: Chorus is a security gatekeeper — agents must request permission, get approved or blocked, and everything is logged

Think: Auth0 / permission manager / security control room, but for AI agents.

---

## What Chorus Will Do

- Connect external accounts (Gmail, GitHub, etc.)
- Register agents and assign them capabilities (permissions)
- Enforce policy on every agent action before it executes
- Route sensitive actions through a human approval queue
- Block or quarantine agents that repeatedly attempt risky actions
- Keep an immutable audit log of every decision

---

## Capabilities (Permissions)

A capability is a named permission scoped to a provider action.

| Capability | Meaning |
|---|---|
| `gmail.draft.create` | Agent can create Gmail drafts |
| `github.issue.create` | Agent can create GitHub issues |
| `github.pull_request.merge` | Agent can merge pull requests |

---

## Decision Outcomes

When an agent requests an action, the system responds with one of:

1. **Allow** — execute immediately
2. **Allow + log** — execute but flag for review
3. **Require approval** — pause and wait for human decision
4. **Block** — deny the action
5. **Quarantine** — deny and restrict the agent from further attempts

---

## The Demo Story (3 Agents)

| Agent | Action | Outcome |
|---|---|---|
| Assistant Agent | Create Gmail draft | Auto-allowed |
| Builder Agent | Create GitHub issue | Paused for human approval |
| Ops Agent | Merge a PR | Blocked → quarantined on repeat |

---

## Backend Modules Being Built

- `auth` — user identity (mock or Auth0)
- `vault` — token storage, keeps credentials off agents
- `connections` — linked provider accounts
- `agents` — agent registry and capability grants
- `policy` — deterministic capability/scope checks
- `risk` — action risk scoring (low / medium / high / critical), optional Gemini explanation
- `enforcement` — combines policy + risk into a final decision
- `actions` — action request lifecycle and execution
- `approvals` — human approval queue and resolution
- `audit` — immutable event history
- `providers` — Gmail and GitHub adapters (mock-first)

---

## Frontend Dashboard Pages

- Connected Accounts
- Agents & Permissions
- Pending Approvals
- Activity Timeline
- Quarantine State

---

## What's Being Removed

- Kafka, Datadog, ElevenLabs from the default startup path
- Old prediction-engine demo complexity
- These may remain as a legacy mode but won't be in the main flow

---

## Storage

- SQLite for persisted state
- In-process WebSocket fanout for live dashboard updates (no external broker in MVP)
- Redis kept for live updates / temporary state in later phases

---

## Commit Plan (Backend Dev's Roadmap)

1. Planning docs
2. Simplify runtime, remove old demo deps
3. DB / config / module structure
4. Auth + token/account connection layer
5. Agents + permissions
6. Policy / risk / enforcement logic
7. Action execution + audit logging
8. Approvals + quarantine
9. Frontend build
10. Seeded demo + smoke tests
11. README + docs rewrite
