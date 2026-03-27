# Testing & Integration Guide

## Overview

This document outlines the testing strategy, coverage, and integration reports for the Chorus system. It includes details on unit, integration, and end-to-end testing.

## Test Strategy

### Layers
1. **Unit Tests**: Isolated logic (e.g., trust score calculation).
2. **Integration Tests**: Component interaction (e.g., Kafka -> StreamProcessor).
3. **Property-Based Tests**: Invariants checking (using Hypothesis).
4. **End-to-End Tests**: Full system flow (Agent -> Dashboard).

### Running Tests

```bash
cd backend
source venv/bin/activate

# All tests
pytest

# Integration tests only
pytest -m integration

# Property-based tests only
pytest -m property

# Specific test file
pytest tests/test_integration_realtime_dataflow.py
```

---

## Real-Time Data Flow Integration Tests

**File**: `tests/test_integration_realtime_dataflow.py`

### Coverage
1. **Complete Message Flow**: Agent -> Kafka -> StreamProcessor -> EventBridge -> Dashboard.
2. **Kafka Topic Creation**: Verification of topic creation on startup.
3. **Graceful Degradation**: System behavior when Kafka is unavailable (local buffering).
4. **Event Sourcing**: Event persistence and replay functionality.
5. **Concurrent Processing**: Handling multiple agents simultaneously.
6. **Metrics Collection**: Throughput and latency tracking.
7. **Pattern Detection**: Routing loops, resource hoarding, etc.

### Mocking Strategy
- **Redis**: In-memory mock.
- **Gemini API**: Predictable mock responses.
- **Kafka**: Can be mocked or real (via `KAFKA_ENABLED` env var).

---

## System Integration Report (Dec 2025)

### Status: ✅ COMPLETED

### Validation Results
- **Core System**: 100% functional (Simulation, Conflict Prediction, Trust Management).
- **Property Tests**: 109/109 passed.
- **Failure Recovery**: Circuit breakers and error handling verified.

### Integration Points
- **Redis**: Verified trust score persistence.
- **Datadog**: Verified metrics submission.
- **Kafka**: Verified event streaming and buffering.
- **Frontend**: Verified WebSocket connectivity.

### Known Issues
- Minor JSON serialization issue with DateTime objects in quarantine actions.
- Occasional flakiness in timing-dependent integration tests.

---

## Load & Performance Testing

**File**: `src/load_testing.py`

### Features
- **KafkaLoadTester**: Producer/Consumer throughput testing.
- **StreamProcessingLoadTester**: End-to-end latency validation.
- **PerformanceBenchmarkSuite**: Automated pass/fail against baselines.

### Targets
- **Throughput**: > 100 msg/s.
- **Latency**: P95 < 500ms.
- **Error Rate**: < 1%.

To run benchmarks:
```bash
python performance_benchmark.py full --output results.json
```
