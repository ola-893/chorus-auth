# Requirements Document - Datadog & Confluent Enhancement

## Introduction
To secure the Datadog and Confluent prizes in the Google Cloud Partner Hackathon, the Chorus project requires enhanced observability specifically tailored for LLM applications. This specification outlines the addition of detailed LLM telemetry (tokens, latency) and a deployable Datadog dashboard, alongside the existing business metrics.

## Requirements

### Requirement 1: LLM Operational Telemetry
**User Story:** As a Datadog judge or system operator, I want to see detailed operational metrics for the Gemini LLM, so that I can understand the cost and performance of the AI component.

#### Acceptance Criteria
1.  **Token Tracking:** The system SHALL measure and report `prompt_token_count` and `candidates_token_count` (completion tokens) for every Gemini API call.
2.  **Latency Tracking:** The system SHALL measure and report the exact execution time of Gemini API calls.
3.  **Finish Reason:** The system SHALL report the finish reason (e.g., STOP, MAX_TOKENS) to identify truncated responses.
4.  **Metric Namespace:** All metrics SHALL use the `chorus.gemini.*` namespace.

### Requirement 2: Deployable Datadog Dashboard
**User Story:** As a Datadog judge, I want a single-file JSON dashboard definition, so that I can immediately visualize the system's health and LLM performance without manual setup.

#### Acceptance Criteria
1.  **Dashboard File:** A `dashboard.json` file SHALL be created in `infrastructure/datadog/`.
2.  **LLM Widgets:** The dashboard SHALL include graphs for Token Usage (Cost) and Latency.
3.  **Business Widgets:** The dashboard SHALL include graphs for Conflict Risk Scores and Agent Trust Scores.
4.  **Operational Widgets:** The dashboard SHALL include graphs for Active Agents and Error Rates.
5.  **Variables:** The dashboard SHALL support template variables for `env` (e.g., prod, dev).

### Requirement 3: Confluent/Kafka Reliability
**User Story:** As a Confluent judge, I want to see that the event streaming architecture is robust and observable.

#### Acceptance Criteria
1.  **Kafka Metrics:** Ensure Kafka producer/consumer metrics are being sent to Datadog (Message rate, Lag). *Note: Basic integration exists, need to verify it covers these.*
