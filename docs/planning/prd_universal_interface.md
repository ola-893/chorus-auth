# Product Requirements Document (PRD) - Chorus Universal Interface
Version: 1.0
Status: For Development & Hackathon Submission
Author: Chorus Team
Date: December 20, 2025

## 1. Executive Summary & Vision
Chorus is evolving from a bespoke safety layer for specific agent networks into a universal safety-as-a-service protocol. This document defines the requirements for a standardized interface that allows any decentralized multi-agent system (MAS) to integrate Chorus's conflict prediction, trust scoring, and intervention capabilities as a non-invasive, plug-and-play module.

**Vision Statement:** To become the foundational immune system layer for the decentralized agent internet, enabling safe, reliable, and emergent-failure-resistant agent interactions across all platforms.

## 2. Problem Statement
The nascent decentralized agent ecosystem lacks standardized safety infrastructure. Each platform (AgentVerse, LangGraph, CrewAI, custom networks) must independently build complex, non-core safety logic, leading to:
- **Duplicated Effort:** Reinvention of conflict detection, game theory, and quarantine systems.
- **Inconsistent Safety:** Varying levels of protection create ecosystem-wide fragility.
- **High Integration Barrier:** Platforms cannot easily adopt battle-tested safety solutions.
- **Limited Observability:** No cross-network visibility into emergent failure patterns.

## 3. Goals & Success Metrics
| Goal | Success Metric |
|------|----------------|
| **G1: Universal Interoperability** | Support 3+ distinct agent network architectures (push-based, pull-based, event-driven) via adapters within 3 months. |
| **G2: Minimal Integration Friction** | New network integration time reduced to <2 developer days, as measured by a published "Quickstart Guide." |
| **G3: Non-Invasive Operation** | Zero required changes to the host network's core agent logic for basic monitoring. |
| **G4: Demonstrable Value** | Show a 90%+ reduction in simulated cascade failures for integrated networks in benchmark tests. |
| **G5: Hackathon Validation** | Deliver a working Universal Observer API and a refined AgentVerse adapter as a proof-of-concept for the current submission. |

## 4. User Personas & Stories
| Persona | Job-to-be-Done (JTBD) | User Story |
|---------|-----------------------|------------|
| **Platform Engineer (Primary)** | "I need to make our agent network resilient without rewriting our core protocol." | As a Platform Engineer, I want to install a Chorus SDK so that I can stream agent events to the safety network and receive interventions via webhook, without modifying individual agent code. |
| **Agent Developer** | "I want my agents to be good citizens in any network they join." | As an Agent Developer, I want my agent to carry a Chorus-compatible identity and trust score so that it can prove its reliability when interacting in new ecosystems. |
| **System Operator** | "I need a single pane of glass for safety across all my agent deployments." | As a System Operator, I want to connect multiple, heterogeneous agent fleets (AgentVerse, private cluster) to one Chorus dashboard so I can see cross-network threats and correlations. |

## 5. Core Requirements

### 5.1 Universal Observer API (REQ-OBS-001)
**Description:** A secure, idempotent REST endpoint for networks to push agent interaction data.
**Acceptance Criteria:**
- Must accept payloads conforming to the `ChorusObservation` schema.
- Must authenticate requests via API key (per network) or JWT.
- Must return HTTP 202 Accepted immediately upon validation, processing asynchronously.
- Must deduplicate events based on `network_id` + `event_id` within a 5-minute window.

### 5.2 Adapter SDK & Abstraction Layer (REQ-ADP-001)
**Description:** A well-defined `BaseNetworkAdapter` interface and helper SDKs to build network-specific connectors.
**Acceptance Criteria:**
- Must provide a Python `BaseNetworkAdapter` ABC with `fetch_events()` and `execute_intervention()` methods.
- Must include a reference implementation (AgentVerse Adapter).
- Must allow adapters to run as standalone services or within the host network's process.

### 5.3 Intervention Gateway & Webhook System (REQ-INT-001)
**Description:** A configurable system for Chorus to send safety interventions back to source networks.
**Acceptance Criteria:**
- Each registered network must be able to specify a secure webhook endpoint.
- Interventions must follow the `ChorusIntervention` schema (QUARANTINE, THROTTLE, ALERT).
- Must implement retry logic with exponential backoff for failed webhook deliveries.
- Must provide a dashboard for operators to view intervention status and history.

### 5.4 Agent Identity & Trust Portability (REQ-ID-001)
**Description:** A mechanism for agents to maintain a persistent identity and trust score across different integrated networks.
**Acceptance Criteria:**
- Must support agent identifiers that are globally unique or namespaced per network.
- Must allow trust score queries via a secure API (`GET /v1/agents/{agent_id}/trust`).
- Trust score adjustments must be attributable to specific networks and incidents for audit.

### 5.5 Comprehensive Observability Suite (REQ-DASH-001)
**Description:** Extend the existing Chorus dashboard to visualize data from multiple integrated networks.
**Acceptance Criteria:**
- Dashboard must have a network selector to filter views.
- Must display a unified causal graph showing interactions across network boundaries.
- All alerts and metrics must be tagged with source `network_id`.

## 6. Non-Functional Requirements
- **Performance:** Observer API must sustain 10,000 events/sec per network with <100ms p95 latency.
- **Security:** All network-to-Chorus and Chorus-to-network communications must use TLS 1.3. API keys must be rotatable without downtime.
- **Extensibility:** The adapter system must allow a developer to integrate a new, simple network within 48 hours.
- **Operational:** The system must provide health status for all integrated networks and their connection adapters.

## 7. Out of Scope (v1.0)
- Real-time, bidirectional agent-to-agent mediation (full proxy mode).
- On-premise deployment of the entire Chorus core.
- Autonomous negotiation of service-level agreements (SLAs) between networks.
- Billing and multi-tenant isolation (beyond simple API keys).

## 8. Milestones & Roadmap
- **Milestone 1 (Hackathon Submission):** Working Universal Observer API, Refactored AgentVerse Adapter, Design Docs.
- **Milestone 2 (Post-Hackathon, 1 Month):** Python Adapter SDK, Webhook System, Enhanced Dashboard.
- **Milestone 3 (2 Months):** Two new reference adapters (e.g., for LangGraph & a generic REST API), Public "Integration Playground."
- **Milestone 4 (3 Months):** Public beta launch, Trust Portability API, First external platform integration.
