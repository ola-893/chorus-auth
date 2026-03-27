# Auth Control Plane Requirements

## Introduction

Refactor Chorus from a multi-agent conflict prediction system into a secure authorization and intervention control plane for AI agents. The refactor must center the product on delegated access, scoped agent permissions, approval workflows, auditability, and policy-driven enforcement using Auth0 and Token Vault abstractions.

## Glossary

- **Control Plane**: The backend and dashboard layer that governs whether an agent action is allowed, escalated, blocked, or quarantined.
- **Connected Account**: A user-linked external provider account, such as Gmail or GitHub, with known scopes and status.
- **Capability**: A named permission describing an action an agent may request.
- **Action Request**: A single request from an agent to perform a provider action through Chorus.
- **Risk Assessment**: A classification and explanation of the risk associated with an action request.
- **Approval Decision**: A user-recorded decision approving or rejecting a risky action.
- **Quarantine**: A state in which an agent is prevented from executing further requests after repeated violations.
- **Vault Adapter**: The abstraction responsible for retrieving delegated provider access without exposing raw credentials to agents.

## Requirements

### Requirement 1

**User Story:** As a user delegating work to AI agents, I want Chorus to authenticate me and associate my identity with my accounts and agents, so that all delegated actions remain attributable to me.

#### Acceptance Criteria

1. WHEN a user loads the application THEN the system SHALL resolve the current authenticated user through a mock or live Auth0-backed adapter
2. WHEN the current user is resolved THEN the system SHALL return user identity data through `GET /api/me`
3. WHEN the system is running in mock mode THEN the system SHALL provide a deterministic seeded user without requiring external credentials
4. WHEN an action is evaluated or executed THEN the system SHALL associate the action with the owning user

### Requirement 2

**User Story:** As a user, I want to connect external accounts for agent delegation, so that Chorus can mediate provider access without exposing credentials directly to agents.

#### Acceptance Criteria

1. WHEN a user views connected accounts THEN the system SHALL list provider, scope, status, and connection mode
2. WHEN a user creates a connected account THEN the system SHALL persist provider metadata and granted scopes
3. WHEN a provider token is needed for an approved action THEN the system SHALL retrieve access only through the vault adapter
4. WHEN the vault adapter is in mock mode THEN the system SHALL return deterministic provider access metadata for demo execution

### Requirement 3

**User Story:** As a user managing multiple agents, I want to create and inspect agents with explicit statuses, so that I can understand who may act on my behalf.

#### Acceptance Criteria

1. WHEN a user creates an agent THEN the system SHALL persist the agent with a unique identifier, type, status, and description
2. WHEN a user lists agents THEN the system SHALL return agent status including active or quarantined state
3. WHEN a user views an agent THEN the system SHALL include granted capabilities and recent action activity
4. WHEN an agent is quarantined THEN the UI SHALL clearly indicate the quarantine reason and timestamp

### Requirement 4

**User Story:** As a user, I want to grant scoped capabilities to agents, so that each agent receives least-privilege access only for approved tasks.

#### Acceptance Criteria

1. WHEN a capability grant is created THEN the system SHALL associate an agent, capability, and optional constraints
2. WHEN a capability is evaluated THEN the system SHALL validate provider and action type compatibility
3. WHEN an action falls outside a granted capability THEN the system SHALL reject the request before execution
4. WHEN the dashboard shows agent details THEN the system SHALL display granted capabilities with readable labels

### Requirement 5

**User Story:** As an agent platform operator, I want all actions to enter the system through a central request pipeline, so that policy, risk, approval, and audit behavior are enforced consistently.

#### Acceptance Criteria

1. WHEN an agent submits an action THEN the system SHALL persist an `ActionRequest`
2. WHEN an action request is created THEN the system SHALL assign an initial lifecycle status
3. WHEN the request pipeline runs THEN the system SHALL evaluate policy before provider execution
4. WHEN a direct provider execution path is attempted outside the pipeline THEN the system SHALL not expose a bypassing API

### Requirement 6

**User Story:** As a security-conscious user, I want deterministic policy checks, so that obvious violations are blocked even if the LLM is unavailable.

#### Acceptance Criteria

1. WHEN a request is evaluated THEN the system SHALL validate capability grants and provider restrictions using deterministic rules
2. WHEN a request violates a hard rule THEN the system SHALL return a block decision with an explanation
3. WHEN deterministic policy allows a request THEN the system SHALL continue to risk evaluation
4. WHEN the policy engine blocks a request THEN the system SHALL append an audit event describing the reason

### Requirement 7

**User Story:** As a user, I want risk evaluation to consider context and not just static permissions, so that unusual actions can trigger review instead of being silently executed.

#### Acceptance Criteria

1. WHEN an action request is evaluated THEN the system SHALL produce a risk level, explanation, and enforcement recommendation
2. WHEN Gemini is available THEN the system SHALL optionally add contextual reasoning to the risk explanation
3. WHEN Gemini is unavailable THEN the system SHALL fall back to deterministic risk logic without failing the request pipeline
4. WHEN a risk decision is shown in the UI THEN the system SHALL include a human-readable explanation

### Requirement 8

**User Story:** As a user, I want risky actions to require explicit approval, so that I remain in control of sensitive delegated operations.

#### Acceptance Criteria

1. WHEN an action is classified as requiring approval THEN the system SHALL create a pending approval record
2. WHEN a user views pending approvals THEN the system SHALL list the action, agent, provider, requested capability, and reason
3. WHEN a user approves an action THEN the system SHALL resume execution through the standard action pipeline
4. WHEN a user rejects an action THEN the system SHALL mark the request as rejected and append an audit event

### Requirement 9

**User Story:** As a user, I want all action outcomes recorded in a clear timeline, so that I can audit what happened and why.

#### Acceptance Criteria

1. WHEN an action request changes state THEN the system SHALL append an audit event
2. WHEN an action is executed THEN the system SHALL persist an execution record with status and provider summary
3. WHEN the dashboard loads THEN the system SHALL provide a timeline of requests, decisions, and outcomes
4. WHEN the dashboard receives live updates THEN new timeline entries SHALL appear without a full page reload

### Requirement 10

**User Story:** As a user, I want Chorus to intervene after repeated risky or disallowed behavior, so that compromised or overreaching agents are contained quickly.

#### Acceptance Criteria

1. WHEN an agent repeatedly triggers block-worthy behavior THEN the system SHALL create a quarantine record
2. WHEN an agent is quarantined THEN future action requests from that agent SHALL be denied automatically
3. WHEN the system denies a quarantined agent THEN the response SHALL explain that the agent is quarantined
4. WHEN the dashboard loads quarantined agents THEN it SHALL show the trigger reason and current state

### Requirement 11

**User Story:** As a demo audience member, I want the app to prove the delegated authorization story quickly, so that the product value is obvious in under a minute.

#### Acceptance Criteria

1. WHEN the seeded demo starts THEN the system SHALL create one user, two connected accounts, and three agents
2. WHEN the demo scenario runs THEN the system SHALL support one auto-allowed Gmail draft, one approval-required GitHub issue, and one blocked then quarantined GitHub merge
3. WHEN the demo is launched via `run_frontend_demo.sh` THEN Kafka, Datadog, and ElevenLabs SHALL not be required
4. WHEN the demo is used offline from live provider credentials THEN mock auth, vault, and provider modes SHALL still demonstrate the full control flow

### Requirement 12

**User Story:** As a maintainer, I want the repository to expose one supported runtime path, so that the MVP stays easy to run, explain, and maintain.

#### Acceptance Criteria

1. WHEN the application boots THEN it SHALL start the auth control plane directly without a legacy mode switch
2. WHEN the demo is launched THEN Kafka, Datadog, ElevenLabs, and any external broker or cache SHALL not be required services
3. WHEN obsolete prediction-era modules are removed THEN the default README, scripts, and compose path SHALL continue to work
4. WHEN new code is introduced THEN the implementation SHALL use SQLite for persisted MVP state and the in-process websocket event stream for live dashboard updates
