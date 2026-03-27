# Environment Variables Reference

This document provides a comprehensive reference for all environment variables used by the Chorus Agent Conflict Predictor system.

## Core Configuration

### Environment Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CHORUS_ENVIRONMENT` | Yes | `development` | Deployment environment: `development`, `testing`, `staging`, `production` |
| `CHORUS_DEBUG` | No | `false` | Enable debug mode with verbose logging |

## Google Gemini API Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CHORUS_GEMINI_API_KEY` | Yes | - | Google Gemini API key for conflict prediction |
| `CHORUS_GEMINI_MODEL` | No | `gemini-3-pro-preview` | Gemini model to use for analysis |
| `CHORUS_GEMINI_TIMEOUT` | No | `30.0` | API request timeout in seconds |
| `CHORUS_GEMINI_MAX_RETRIES` | No | `3` | Maximum retry attempts for failed requests |

## Redis Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CHORUS_REDIS_HOST` | Yes | `localhost` | Redis server hostname or IP address |
| `CHORUS_REDIS_PORT` | No | `6379` | Redis server port number |
| `CHORUS_REDIS_PASSWORD` | No | - | Redis authentication password (recommended for production) |
| `CHORUS_REDIS_DB` | No | `0` | Redis database number (0-15) |
| `CHORUS_REDIS_POOL_SIZE` | No | `10` | Connection pool size |

## API Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CHORUS_API_HOST` | No | `0.0.0.0` | API server bind address |
| `CHORUS_API_PORT` | No | `8000` | API server port number |
| `CHORUS_API_WORKERS` | No | `1` | Number of API worker processes |

## Agent Simulation Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CHORUS_MIN_AGENTS` | No | `5` | Minimum number of agents in simulation |
| `CHORUS_MAX_AGENTS` | No | `10` | Maximum number of agents in simulation |
| `CHORUS_AGENT_REQUEST_INTERVAL_MIN` | No | `1.0` | Minimum interval between agent requests (seconds) |
| `CHORUS_AGENT_REQUEST_INTERVAL_MAX` | No | `10.0` | Maximum interval between agent requests (seconds) |

## Trust Scoring Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CHORUS_INITIAL_TRUST_SCORE` | No | `100` | Initial trust score for new agents |
| `CHORUS_TRUST_SCORE_THRESHOLD` | No | `30` | Trust score threshold for quarantine |
| `CHORUS_TRUST_CONFLICT_PENALTY` | No | `10` | Trust score penalty for conflicts |
| `CHORUS_TRUST_COOPERATION_BONUS` | No | `1` | Trust score bonus for cooperation |

## Conflict Prediction Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CHORUS_CONFLICT_RISK_THRESHOLD` | No | `0.7` | Risk threshold for intervention (0.0-1.0) |
| `CHORUS_PREDICTION_INTERVAL` | No | `5.0` | Prediction interval in seconds |
| `CHORUS_ANALYSIS_WINDOW` | No | `10` | Number of recent actions to analyze |

## Logging Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CHORUS_LOG_LEVEL` | No | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `CHORUS_LOG_STRUCTURED` | No | `true` | Use structured JSON logging |
| `CHORUS_LOG_FILE_PATH` | No | - | Log file path (if not set, logs to console) |

## Health Check Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CHORUS_HEALTH_CHECK_ENABLED` | No | `true` | Enable health monitoring |
| `CHORUS_HEALTH_CHECK_INTERVAL` | No | `30.0` | Health check interval in seconds |

## Datadog Integration (Optional)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CHORUS_DATADOG_ENABLED` | No | `false` | Enable Datadog integration |
| `CHORUS_DATADOG_API_KEY` | No* | - | Datadog API key (*required if enabled) |
| `CHORUS_DATADOG_APP_KEY` | No* | - | Datadog application key (*required if enabled) |
| `CHORUS_DATADOG_SITE` | No | `datadoghq.com` | Datadog site (e.g., `datadoghq.eu` for EU) |

## ElevenLabs Integration (Optional)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CHORUS_ELEVENLABS_ENABLED` | No | `false` | Enable ElevenLabs voice alerts |
| `CHORUS_ELEVENLABS_API_KEY` | No* | - | ElevenLabs API key (*required if enabled) |
| `CHORUS_ELEVENLABS_VOICE_ID` | No | `21m00Tcm4TlvDq8ikWAM` | Default voice ID for alerts |

## Confluent Kafka Integration (Optional)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `KAFKA_ENABLED` | No | `false` | Enable Kafka event streaming |
| `KAFKA_BOOTSTRAP_SERVERS` | No* | `localhost:9092` | Kafka bootstrap servers (*required if enabled) |
| `KAFKA_AGENT_MESSAGES_TOPIC` | No | `agent-messages-raw` | Topic for raw agent messages |

## Environment-Specific Recommendations

### Development Environment
```bash
CHORUS_ENVIRONMENT=development
CHORUS_DEBUG=true
CHORUS_LOG_LEVEL=DEBUG
CHORUS_MIN_AGENTS=3
CHORUS_MAX_AGENTS=5
CHORUS_REDIS_HOST=localhost
CHORUS_DATADOG_ENABLED=false
```

### Production Environment
```bash
CHORUS_ENVIRONMENT=production
CHORUS_DEBUG=false
CHORUS_LOG_LEVEL=INFO
CHORUS_LOG_STRUCTURED=true
CHORUS_LOG_FILE_PATH=/var/log/chorus/chorus.log
CHORUS_MIN_AGENTS=10
CHORUS_MAX_AGENTS=50
CHORUS_API_WORKERS=4
CHORUS_REDIS_POOL_SIZE=20
CHORUS_DATADOG_ENABLED=true
```

## Security Considerations

1. **Never commit API keys to version control**
2. **Use strong passwords for Redis in production**
3. **Restrict Redis access to localhost or private networks**
4. **Use environment-specific configuration files**
