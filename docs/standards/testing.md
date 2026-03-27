# Chorus Testing Standards

## Test Strategy & Pyramid
- **Unit Tests (70%)**: Fast, isolated tests for pure functions, utilities, and core logic. Mock all external dependencies (Gemini API, Datadog, etc.).
- **Integration Tests (20%)**: Test interactions between our services and *actual* partner APIs in a test/staging environment.
- **E2E Tests (10%)**: Critical user journey tests with the full system deployed.

## Unit Testing (pytest)
### Structure
- Place test files in a `tests/` directory mirroring the source `src/` structure.
- Test class names: `Test{OriginalClass}`
- Test method names: `test_{scenario}_{expected_result}` (e.g., `test_low_trust_agent_gets_quarantined`).

### Mocking
- Use `unittest.mock` to mock external API calls.
- For the Gemini client, mock the `google.genai.Client` class and its `generate_content` method.
- Validate that mocks are called with the expected arguments.

## Integration Testing
- Use dedicated test API keys and resources for Datadog, Confluent, and ElevenLabs.
- Tests must clean up any data they create.
- Tag integration tests with `@pytest.mark.integration` and run them separately from the unit test suite.

## E2E & Scenario Testing
- Define key user stories and failure scenarios (e.g., "CDN cache stampede is predicted and prevented").
- Use scripts or a testing framework to simulate agent behavior and verify system intervention.
- These tests are allowed to be slower and run less frequently (e.g., in CI before a release).

## Coverage & Quality Gates
- Minimum **80%** overall code coverage.
- **95%+ coverage** for critical paths: conflict prediction engine, trust scoring, and quarantine logic.
- No decrease in coverage percentage on a pull request.