# API Standards

The active API surface is the auth control plane API under `/api`.

## Design Principles

- Use resource-oriented routes.
- Return explicit lifecycle states such as `pending_approval`, `completed`, or `quarantined`.
- Prefer human-readable explanations for allow, block, approval, and quarantine outcomes.
- Keep provider-specific execution details normalized before returning them to the UI.

## Active Endpoints

### Identity

- `GET /api/me`

### Connected Accounts

- `GET /api/connections`
- `POST /api/connections`

### Agents

- `GET /api/agents`
- `POST /api/agents`
- `GET /api/agents/{id}`
- `POST /api/agents/{id}/capability-grants`

### Actions

- `GET /api/actions`
- `POST /api/actions`
- `GET /api/actions/{id}`

### Approvals

- `GET /api/approvals`
- `POST /api/approvals/{id}/approve`
- `POST /api/approvals/{id}/reject`

### Audit

- `GET /api/audit`
- `GET /api/audit/{action_id}`

### Realtime

- `GET /ws/dashboard`

## Error Handling

- Use standard HTTP status codes.
- Return `404` when an owned resource does not exist.
- Return `409` when approval state changes are attempted on already resolved requests.
- Return explanatory error messages that help the operator recover quickly.
