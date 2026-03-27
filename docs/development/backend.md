# Backend Development Guide

## Overview

The Chorus backend is built with Python and FastAPI, designed to provide real-time conflict prediction and intervention for decentralized multi-agent networks. It leverages Google's Gemini 3 Pro API for game theory analysis.

## Project Structure

```
backend/
├── src/                           # Source code
│   ├── prediction_engine/         # Core prediction engine
│   │   ├── models/               # Data models and types
│   │   ├── game_theory/          # Game theory analysis components
│   │   └── interfaces.py         # Base interfaces for all components
│   ├── integrations/             # External service integrations
│   ├── api/                      # FastAPI REST endpoints
│   ├── config.py                 # Configuration management
│   └── logging_config.py         # Logging setup
├── tests/                        # Test suite
├── requirements.txt              # Python dependencies
├── pytest.ini                   # Pytest configuration
├── conftest.py                   # Pytest fixtures
├── setup.py                      # Package setup
├── setup_env.sh                  # Environment setup script
└── .env.example                  # Example environment configuration
```

## Quick Start for Developers

1. **Set up the environment:**
   ```bash
   ./setup_env.sh
   ```

2. **Activate the virtual environment:**
   ```bash
   source venv/bin/activate
   ```

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

4. **Run the development server:**
   ```bash
   python src/main.py
   # or
   uvicorn src.api.main:app --reload
   ```

## Core Components

### Interfaces
- **Agent**: Base interface for autonomous agents
- **GeminiClient**: Interface for Google Gemini API integration
- **TrustManager**: Interface for managing agent trust scores
- **InterventionEngine**: Interface for quarantine and intervention logic
- **ResourceManager**: Interface for shared resource management
- **AgentNetwork**: Interface for agent simulation orchestration

### Data Models
- **AgentIntention**: Represents an agent's intention to perform an action
- **ConflictAnalysis**: Result of game theory conflict analysis
- **TrustScoreEntry**: Trust score record for agents
- **QuarantineAction**: Record of quarantine interventions
- **ResourceRequest**: Request for shared resources

## Code Quality Standards

- **Formatting**: `black src tests`
- **Linting**: `flake8 src tests`
- **Type Checking**: `mypy src`
- **Coverage**: Minimum 80% overall, 95% for critical paths.

## Architecture Layers

1. **API Layer**: FastAPI endpoints for external interaction.
2. **Control Layer**: Intervention Engine for safety mechanisms.
3. **Analysis Layer**: Gemini-powered conflict prediction and Redis-backed trust management.
4. **Integration Layer**: Connectors for Gemini, Datadog, ElevenLabs, and Confluent Kafka.

## Testing

Run tests using pytest:

```bash
pytest                       # Run all tests
pytest -m "not integration"  # Unit tests only
pytest -m integration        # Integration tests only
pytest -m property          # Property-based tests only
```
