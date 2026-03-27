# Tasks - Datadog & Confluent Enhancement

- [x] 1. Update `DatadogClient`
    - Modify `backend/src/integrations/datadog_client.py`.
    - Add `track_llm_usage` method.
    - Ensure metrics are sent with correct types (count vs gauge) and tags (model, env).

- [x] 2. Instrument `GeminiClient`
    - Modify `backend/src/prediction_engine/gemini_client.py`.
    - Import `time` module.
    - Wrap `generate_content` calls to measure latency.
    - Extract token counts from `response.usage_metadata`.
    - Call `datadog_client.track_llm_usage`.
    - Handle cases where metadata might be missing (graceful fallback).

- [x] 3. Create Datadog Dashboard
    - Create `infrastructure/datadog/dashboard.json`.
    - Define the JSON structure with required widgets.
    - Ensure queries match the metric names defined in Task 1 (`chorus.gemini.*`).

- [x] 4. Verification
    - Run a simulation (e.g., `backend/demo_simulation.py` or existing tests) to generate traffic.
    - (Self-Verification) Check logs to ensure `track_llm_usage` is being called and metrics are queued.