# Design Document - Datadog & Confluent Enhancement

## Overview
This design focuses on instrumenting the `GeminiClient` to extract low-level usage metadata from the Google Gen AI SDK and piping it into Datadog via the `DatadogClient`. Additionally, it defines the structure of the JSON dashboard.

## Components

### 1. DatadogClient Extension
We will extend `backend/src/integrations/datadog_client.py`.

**New Method:**
```python
def track_llm_usage(self, 
                    model: str, 
                    prompt_tokens: int, 
                    completion_tokens: int, 
                    latency_ms: float,
                    finish_reason: str):
    """
    Tracks LLM usage metrics.
    Metrics:
    - chorus.gemini.tokens.prompt (count)
    - chorus.gemini.tokens.completion (count)
    - chorus.gemini.tokens.total (count)
    - chorus.gemini.latency (gauge)
    - chorus.gemini.request (count, tagged by finish_reason)
    """
```

### 2. GeminiClient Instrumentation
We will modify `backend/src/prediction_engine/gemini_client.py`.

**Logic:**
1.  Start timer before `_client.generate_content`.
2.  Stop timer after response.
3.  Extract `usage_metadata` from response object.
    *   `response.usage_metadata.prompt_token_count`
    *   `response.usage_metadata.candidates_token_count`
4.  Call `datadog_client.track_llm_usage`.

### 3. Dashboard Definition (`dashboard.json`)
A JSON file compatible with Datadog's "Import Dashboard" feature.

**Layout:**
*   **Row 1: High Level Status** (System Health, Active Agents, Conflict Risk)
*   **Row 2: LLM Performance** (Latency p95, Token Usage over time)
*   **Row 3: Agent Insights** (Trust Score Distribution, Quarantine Count)
*   **Row 4: Infrastructure** (Kafka Throughput, Error Logs)

## Data Flow
`Gemini API` -> `GeminiClient` -> (Extract Metadata) -> `DatadogClient` -> `Datadog API` -> `Datadog Dashboard`
