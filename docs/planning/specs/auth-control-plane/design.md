# Auth Control Plane Design Document

## Overview

This design refactors Chorus into a secure control plane for delegated AI actions. The new architecture preserves the useful intervention ideas from the legacy system but reorients them around authorization, enforcement, approval, and auditability rather than trust-score-driven swarm monitoring.

The MVP favors a boring and demo-stable stack: FastAPI, SQLite, React, mock-first Auth0 and Token Vault adapters, in-process WebSocket fanout, and provider adapters for Gmail and GitHub. Kafka, Datadog, and ElevenLabs remain outside the default execution path.

## Architecture

### System Context

```
User Dashboard
    |
    v
FastAPI Control Plane
    |
    +--> Auth Adapter
    +--> Vault Adapter
    +--> Agent Registry
    +--> Policy Engine
    +--> Risk Engine
    +--> Enforcement Engine
    +--> Approval Service
    +--> Provider Adapters
    +--> Audit Timeline
    |
    +--> SQLite
    +--> In-Memory Event Stream
```

### Application Flow

1. The dashboard resolves the current user and loads connected accounts, agents, approvals, and audit history.
2. An agent submits an `ActionRequest`.
3. The policy engine validates capability grants and provider restrictions.
4. The risk engine assigns a risk level and explanation using deterministic rules and optional Gemini context.
5. The enforcement engine maps the result to `ALLOW`, `ALLOW_WITH_AUDIT`, `REQUIRE_APPROVAL`, `BLOCK`, or `QUARANTINE`.
6. If allowed, the provider adapter executes using vault-mediated provider access.
7. Every state transition appends an audit event and emits a dashboard update over WebSocket.

## Components and Interfaces

### `db`

Responsibilities:
- SQLAlchemy engine and session management
- Declarative ORM models
- Alembic migration configuration
- Seed helpers for demo mode

Key interfaces:
- `get_session()`
- `Base`
- ORM models for users, agents, capabilities, action requests, approvals, execution, quarantine, and audit

### `auth`

Responsibilities:
- Resolve current user through mock or live Auth0-backed adapter
- Normalize user identity into the control plane
- Expose `GET /api/me`

Key interfaces:
- `AuthAdapter`
- `MockAuthAdapter`
- `Auth0AuthAdapter`
- `get_current_user()`

### `vault`

Responsibilities:
- Retrieve provider access metadata without exposing raw credentials to agents
- Support mock and future live Token Vault implementations

Key interfaces:
- `VaultAdapter`
- `MockVaultAdapter`
- `TokenVaultAdapter`
- `get_provider_access(user_id, provider)`

### `connections`

Responsibilities:
- Persist connected accounts
- Expose list/create APIs for demo providers
- Associate provider scopes and status with a user

Key interfaces:
- `ConnectedAccountService`
- `GET /api/connections`
- `POST /api/connections`

### `agents`

Responsibilities:
- Create and list agents
- Register capabilities and grants
- Surface quarantine state on agent details

Key interfaces:
- `AgentService`
- `CapabilityService`
- `GET /api/agents`
- `POST /api/agents`
- `POST /api/agents/{id}/capability-grants`

### `policy`

Responsibilities:
- Deterministic least-privilege checks
- Provider-specific restrictions
- Early rejection of invalid or disallowed actions

Key interfaces:
- `PolicyDecision`
- `PolicyEngine.evaluate(request, grants, account)`

### `risk`

Responsibilities:
- Deterministic risk scoring
- Optional Gemini-powered contextual explanation
- Normalize risk output for enforcement

Key interfaces:
- `RiskLevel`
- `RiskAssessmentResult`
- `RiskEngine.assess(request, context)`

### `enforcement`

Responsibilities:
- Combine policy and risk into a final outcome
- Apply quarantine escalation when repeat violations occur

Key interfaces:
- `EnforcementDecision`
- `EnforcementEngine.decide(policy_result, risk_result, history)`

### `actions`

Responsibilities:
- Persist action requests
- Drive lifecycle transitions
- Call provider adapters after final decisions

Key interfaces:
- `ActionRequestService`
- `POST /api/actions`
- `GET /api/actions`
- `GET /api/actions/{id}`

### `approvals`

Responsibilities:
- Persist approval requests and decisions
- Resume or close the action lifecycle

Key interfaces:
- `ApprovalService`
- `GET /api/approvals`
- `POST /api/approvals/{id}/approve`
- `POST /api/approvals/{id}/reject`

### `providers`

Responsibilities:
- Mock-first execution for Gmail and GitHub
- Payload validation and result normalization

Key interfaces:
- `ProviderAdapter`
- `GmailProviderAdapter`
- `GitHubProviderAdapter`

### `audit`

Responsibilities:
- Append-only audit event recording
- Timeline queries and realtime publishing

Key interfaces:
- `AuditService`
- `GET /api/audit`
- `GET /api/audit/{action_id}`
- dashboard event publisher

## Data Model

### Relational Entities

- `User`
- `Agent`
- `ConnectedAccount`
- `Capability`
- `AgentCapabilityGrant`
- `ActionRequest`
- `RiskAssessment`
- `ApprovalDecision`
- `ExecutionRecord`
- `QuarantineRecord`
- `AuditEvent`

### Key Relationships

- A `User` owns many `Agents` and `ConnectedAccounts`
- An `Agent` has many `AgentCapabilityGrant` records
- An `ActionRequest` belongs to a `User` and an `Agent`
- An `ActionRequest` may have one `RiskAssessment`, one `ApprovalDecision`, one `ExecutionRecord`, and many `AuditEvent` entries
- An `Agent` may have zero or more `QuarantineRecord` entries, with at most one active record

## API Design

### REST Endpoints

- `GET /api/me`
- `GET /api/agents`
- `POST /api/agents`
- `GET /api/agents/{id}`
- `POST /api/agents/{id}/capability-grants`
- `GET /api/connections`
- `POST /api/connections`
- `GET /api/actions`
- `POST /api/actions`
- `GET /api/actions/{id}`
- `GET /api/approvals`
- `POST /api/approvals/{id}/approve`
- `POST /api/approvals/{id}/reject`
- `GET /api/audit`
- `GET /api/audit/{action_id}`
- `GET /ws/dashboard`

### WebSocket Contract

Dashboard events should be emitted with a consistent wrapper:

```json
{
  "type": "action.updated",
  "timestamp": "2026-03-27T00:00:00Z",
  "data": {}
}
```

Supported event types:
- `action.created`
- `action.updated`
- `approval.created`
- `approval.updated`
- `agent.quarantined`
- `audit.appended`

## Decision Model

### Deterministic Policy

Examples:
- Missing capability grant -> deny
- Missing connected account -> deny
- Quarantined agent -> deny
- Capability/provider mismatch -> deny

### Deterministic Risk

Examples:
- `gmail.draft.create` -> low
- `github.issue.create` -> medium
- `github.pull_request.merge` -> high
- repeated blocked requests within the configured window -> escalate to quarantine

### Gemini Augmentation

Gemini may enrich:
- explanation text
- contextual warning
- confidence note

Gemini may not:
- bypass hard policy denials
- directly execute actions
- overwrite quarantine state

## Correctness Properties

### Property 1: Capability Enforcement
*For any* action request without a matching capability grant, the system should return a blocking policy decision before provider execution.
**Validates: Requirements 4.3, 5.3, 6.1**

### Property 2: Safe LLM Fallback
*For any* Gemini outage or timeout, the system should still produce a deterministic risk result and continue the request pipeline safely.
**Validates: Requirements 7.3**

### Property 3: Approval Gate Integrity
*For any* action classified as approval-required, the provider adapter should not execute before an approval decision is recorded.
**Validates: Requirements 8.1, 8.3**

### Property 4: Quarantine Enforcement
*For any* action request from an actively quarantined agent, the system should deny the request and append an audit event explaining the quarantine.
**Validates: Requirements 3.4, 10.2, 10.3**

### Property 5: Audit Completeness
*For any* action request state transition, the system should append an audit record and expose it through the timeline API.
**Validates: Requirements 9.1, 9.3**

### Property 6: Demo Determinism
*For any* seeded MVP run in mock mode, the system should expose one allow path, one approval path, and one block-to-quarantine path without external credentials.
**Validates: Requirements 11.1, 11.2, 11.4**

## Operational Notes

- SQLite is the default persisted store for local and demo mode.
- SQLite is the primary source of truth for the MVP.
- Live dashboard updates use the app's in-process event stream and `/ws/dashboard`.
- The auth control plane is the default and only supported local demo path in this repository.
