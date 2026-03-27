# CLI Dashboard Guide

## Overview

The CLI Dashboard provides real-time monitoring of the Chorus Agent Conflict Predictor system through a terminal-based interface. It displays agent status, system metrics, conflict predictions, and intervention actions without requiring user input.

## Features

- **System Status**: Monitor running status and API connections.
- **Agent Monitoring**: Track total, active, and quarantined agents with trust scores.
- **Resource Utilization**: Visual bars for CPU, Memory, Network, and Storage.
- **Conflict Prediction**: Real-time risk scores and predictions.
- **Intervention Tracking**: Log of quarantine actions and reasons.

## Usage

### Basic Usage
```bash
# Start with default settings
python backend/cli_dashboard.py

# Start with specific number of agents
python backend/cli_dashboard.py --agents 7
```

### Demo Mode
Run the dashboard without external dependencies (mock data):
```bash
python backend/demo_cli_dashboard.py
```

### Command Line Options
- `--agents N`: Number of agents to create (5-10).
- `--log-level LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR).
- `--refresh-interval SECONDS`: Dashboard refresh interval (default: 2.0).

## Display Layout

```
CHORUS AGENT CONFLICT PREDICTOR - DASHBOARD
                                                Last Update: 2025-12-14 17:22:07
================================================================================
SYSTEM STATUS:
  Status: 🟢 RUNNING
  Gemini API: 🟢 CONNECTED
--------------------------------------------------------------------------------
AGENT STATUS:
  Total Agents: 8
  Active Agents: 6
  Quarantined Agents: 2
  Trust Scores:
    agent_006:  15 ⚠️
    agent_004:  78 ✅
--------------------------------------------------------------------------------
RESOURCE UTILIZATION:
  cpu         : [███████████████░░░░░]  75.0% 🟡
--------------------------------------------------------------------------------
CONFLICT PREDICTION:
  Current Risk: [█████████████░░░░░░░]  65.0% 🟡 MODERATE
--------------------------------------------------------------------------------
RECENT INTERVENTIONS:
  17:22:03 🚫 QUARANTINE  agent_006   (95%)
    └─ High conflict risk (0.782): Resource contention leading to...
```

## Troubleshooting

1. **Redis Connection Refused**: Ensure Redis is running (`redis-server`).
2. **Gemini API Unavailable**: Check `GEMINI_API_KEY` in `.env`.
3. **Display Issues**: Ensure terminal size is at least 80x30.
