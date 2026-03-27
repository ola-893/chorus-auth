"""
Configuration management for the Chorus Agent Conflict Predictor.
"""
import os
from typing import Optional, Dict, Any, List
from enum import Enum
from pathlib import Path
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Force load .env file to override potentially stale environment variables
load_dotenv(override=True)


class Environment(str, Enum):
    """Supported deployment environments."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Supported log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class GeminiSettings(BaseSettings):
    """Gemini API configuration."""
    model_config = {'env_prefix': 'GEMINI_'}
    
    api_key: str = Field(default="", description="Gemini API key")
    model: str = Field(default="gemini-3-pro-preview", description="Gemini model to use")
    timeout: float = Field(default=30.0, description="API timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay: float = Field(default=1.0, description="Delay between retries in seconds")
    
    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v):
        if v:
            return v.strip()
        return v


class RedisSettings(BaseSettings):
    """Redis configuration."""
    model_config = {'env_prefix': 'REDIS_'}
    
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    password: Optional[str] = Field(default=None, description="Redis password")
    db: int = Field(default=0, description="Redis database number")
    connection_pool_size: int = Field(default=10, description="Connection pool size")
    socket_timeout: float = Field(default=5.0, description="Socket timeout in seconds")
    socket_connect_timeout: float = Field(default=5.0, description="Connection timeout in seconds")
    retry_on_timeout: bool = Field(default=True, description="Retry on timeout")
    
    @field_validator('port')
    @classmethod
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("Redis port must be between 1 and 65535")
        return v
    
    @field_validator('db')
    @classmethod
    def validate_db(cls, v):
        if not 0 <= v <= 15:
            raise ValueError("Redis database number must be between 0 and 15")
        return v


class DatadogSettings(BaseSettings):
    """Datadog configuration."""
    model_config = {'env_prefix': 'DATADOG_'}
    
    api_key: Optional[str] = Field(default=None, description="Datadog API key")
    app_key: Optional[str] = Field(default=None, description="Datadog application key")
    site: str = Field(default="datadoghq.com", description="Datadog site")
    enabled: bool = Field(default=False, description="Enable Datadog integration")


class ElevenLabsSettings(BaseSettings):
    """ElevenLabs configuration."""
    model_config = {'env_prefix': 'ELEVENLABS_'}
    
    api_key: Optional[str] = Field(default=None, description="ElevenLabs API key")
    voice_id: str = Field(default="21m00Tcm4TlvDq8ikWAM", description="Default voice ID")
    model_id: str = Field(default="eleven_turbo_v2", description="Model ID for generation")
    enabled: bool = Field(default=True, description="Enable ElevenLabs integration")
    audio_storage_path: str = Field(default="./backend/alerts", description="Path to store audio files")
    max_audio_age_days: int = Field(default=1, description="Max age of audio files in days")
    
    @model_validator(mode='after')
    def validate_elevenlabs_config(self):
        if self.enabled and not self.api_key:
            raise ValueError("ElevenLabs API key is required when ElevenLabs is enabled")
        return self


class KafkaSettings(BaseSettings):
    """Confluent Kafka configuration."""
    model_config = {'env_prefix': 'KAFKA_'}
    
    bootstrap_servers: str = Field(default="localhost:9092", description="Kafka bootstrap servers")
    security_protocol: str = Field(default="PLAINTEXT", description="Security protocol")
    sasl_mechanism: Optional[str] = Field(default=None, description="SASL mechanism")
    sasl_username: Optional[str] = Field(default=None, description="SASL username")
    sasl_password: Optional[str] = Field(default=None, description="SASL password")
    enabled: bool = Field(default=True, description="Enable Kafka integration")
    buffer_size: int = Field(default=1000, description="Message buffer size for reconnections")
    
    @field_validator('buffer_size')
    @classmethod
    def validate_buffer_size(cls, v):
        if not isinstance(v, int) or v < 0:
            raise ValueError("buffer_size must be a non-negative integer")
        return v
    
    # Topic configuration
    agent_messages_topic: str = Field(default="agent-messages-raw")
    agent_decisions_topic: str = Field(default="agent-decisions-processed")
    system_alerts_topic: str = Field(default="system-alerts")
    causal_graph_updates_topic: str = Field(default="causal-graph-updates")
    analytics_metrics_topic: str = Field(default="analytics-metrics")


class AgentSimulationSettings(BaseSettings):
    """Agent simulation configuration."""
    min_agents: int = Field(default=5, description="Minimum number of agents")
    max_agents: int = Field(default=10, description="Maximum number of agents")
    request_interval_min: float = Field(default=1.0, description="Minimum request interval in seconds")
    request_interval_max: float = Field(default=10.0, description="Maximum request interval in seconds")
    resource_types: List[str] = Field(default=["cpu", "memory", "network", "storage"], description="Available resource types")
    
    @field_validator('min_agents')
    @classmethod
    def validate_min_agents(cls, v):
        if v < 1:
            raise ValueError("Minimum agents must be at least 1")
        return v
    
    @model_validator(mode='after')
    def validate_max_agents(self):
        if self.max_agents < self.min_agents:
            raise ValueError("Maximum agents must be greater than or equal to minimum agents")
        return self


class TrustScoringSettings(BaseSettings):
    """Trust scoring and quarantine configuration."""
    initial_trust_score: int = Field(default=100, description="Initial trust score for new agents")
    quarantine_threshold: int = Field(default=30, description="Trust score threshold for quarantine")
    conflict_penalty: int = Field(default=10, description="Trust score penalty for conflicts")
    cooperation_bonus: int = Field(default=1, description="Trust score bonus for cooperation")
    max_trust_score: int = Field(default=100, description="Maximum trust score")
    min_trust_score: int = Field(default=0, description="Minimum trust score")
    
    @model_validator(mode='after')
    def validate_quarantine_threshold(self):
        if not 0 <= self.quarantine_threshold <= self.max_trust_score:
            raise ValueError(f"Quarantine threshold must be between 0 and {self.max_trust_score}")
        return self


class ConflictPredictionSettings(BaseSettings):
    """Conflict prediction configuration."""
    risk_threshold: float = Field(default=0.7, description="Risk threshold for intervention")
    prediction_interval: float = Field(default=5.0, description="Prediction interval in seconds")
    analysis_window: int = Field(default=10, description="Number of recent actions to analyze")
    
    @field_validator('risk_threshold')
    @classmethod
    def validate_risk_threshold(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Risk threshold must be between 0.0 and 1.0")
        return v


class LoggingSettings(BaseSettings):
    """Logging configuration."""
    level: LogLevel = Field(default=LogLevel.INFO, description="Log level")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="Log format")
    structured: bool = Field(default=True, description="Use structured JSON logging")
    file_path: Optional[str] = Field(default=None, description="Log file path")
    max_file_size: int = Field(default=10485760, description="Maximum log file size in bytes")
    backup_count: int = Field(default=5, description="Number of log file backups to keep")


class HealthCheckSettings(BaseSettings):
    """Health check configuration."""
    enabled: bool = Field(default=True, description="Enable health checks")
    interval: float = Field(default=30.0, description="Health check interval in seconds")
    timeout: float = Field(default=10.0, description="Health check timeout in seconds")
    max_failures: int = Field(default=3, description="Maximum consecutive failures before marking as failed")


class DemoSettings(BaseSettings):
    """Demo configuration."""
    mode_enabled: bool = Field(default=False, description="Enable demo mode")
    audience: str = Field(default="technical", description="Target audience for demo (technical/business)")
    scenario: Optional[str] = Field(default=None, description="Active demo scenario")


class Settings(BaseSettings):
    model_config = {
        'env_file': '.env',
        'env_file_encoding': 'utf-8',
        'extra': 'allow',
        'env_nested_delimiter': '__'
    }
    """Main application settings with environment variable support."""
    
    # Environment configuration
    environment: Environment = Field(default=Environment.DEVELOPMENT, description="Deployment environment")
    debug: bool = Field(default=False, description="Enable debug mode")
    
    # Component configurations
    gemini: GeminiSettings = Field(default_factory=GeminiSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    datadog: DatadogSettings = Field(default_factory=DatadogSettings)
    elevenlabs: ElevenLabsSettings = Field(default_factory=ElevenLabsSettings)
    kafka: KafkaSettings = Field(default_factory=KafkaSettings)
    agent_simulation: AgentSimulationSettings = Field(default_factory=AgentSimulationSettings)
    trust_scoring: TrustScoringSettings = Field(default_factory=TrustScoringSettings)
    conflict_prediction: ConflictPredictionSettings = Field(default_factory=ConflictPredictionSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    health_check: HealthCheckSettings = Field(default_factory=HealthCheckSettings)
    demo: DemoSettings = Field(default_factory=DemoSettings)
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_workers: int = Field(default=1, description="Number of API workers")
    
    # CLI Configuration
    cli_refresh_rate: float = Field(default=1.0, description="CLI refresh rate in seconds")
    cli_max_lines: int = Field(default=50, description="Maximum lines to display in CLI")
        
    @field_validator('environment', mode='before')
    @classmethod
    def validate_environment(cls, v):
        if isinstance(v, str):
            return Environment(v.lower())
        return v
    
    @model_validator(mode='after')
    def validate_production_config(self):
        """Validate production-specific configuration requirements."""
        if self.environment == Environment.PRODUCTION:
            # Ensure critical services are properly configured for production
            if not self.gemini.api_key or self.gemini.api_key.strip() == "":
                raise ValueError("Gemini API key is required in production")
                
            if self.redis.host == 'localhost':
                raise ValueError("Redis host should not be localhost in production")
        
        return self
    
    def get_redis_url(self) -> str:
        """Get Redis connection URL."""
        auth = f":{self.redis.password}@" if self.redis.password else ""
        return f"redis://{auth}{self.redis.host}:{self.redis.port}/{self.redis.db}"
    
    def get_kafka_config(self) -> Dict[str, Any]:
        """Get Kafka configuration dictionary."""
        config = {
            'bootstrap.servers': self.kafka.bootstrap_servers,
            'security.protocol': self.kafka.security_protocol,
        }
        
        if self.kafka.sasl_mechanism:
            config['sasl.mechanism'] = self.kafka.sasl_mechanism
            config['sasl.username'] = self.kafka.sasl_username
            config['sasl.password'] = self.kafka.sasl_password
        
        return config
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration (excluding sensitive data)."""
        return {
            "environment": self.environment.value,
            "debug": self.debug,
            "gemini_model": self.gemini.model,
            "redis_host": self.redis.host,
            "redis_port": self.redis.port,
            "agent_simulation": {
                "min_agents": self.agent_simulation.min_agents,
                "max_agents": self.agent_simulation.max_agents,
            },
            "trust_scoring": {
                "initial_score": self.trust_scoring.initial_trust_score,
                "quarantine_threshold": self.trust_scoring.quarantine_threshold,
            },
            "conflict_prediction": {
                "risk_threshold": self.conflict_prediction.risk_threshold,
                "prediction_interval": self.conflict_prediction.prediction_interval,
            },
            "logging": {
                "level": self.logging.level.value,
                "structured": self.logging.structured,
            },
            "integrations": {
                "datadog_enabled": self.datadog.enabled,
                "elevenlabs_enabled": self.elevenlabs.enabled,
                "kafka_enabled": self.kafka.enabled,
            }
        }


def load_settings(env_file: Optional[str] = None) -> Settings:
    """
    Load settings from environment variables and .env file.
    
    Args:
        env_file: Path to .env file (optional)
        
    Returns:
        Settings instance
    """
    if env_file:
        return Settings(_env_file=env_file)
    return Settings()


def validate_configuration(settings: Settings) -> List[str]:
    """
    Validate configuration and return list of issues.
    
    Args:
        settings: Settings instance to validate
        
    Returns:
        List of validation error messages
    """
    issues = []
    
    # Check required API keys
    if not settings.gemini.api_key:
        issues.append("Gemini API key is required")
    
    # Check Redis connectivity requirements
    if settings.redis.host == "localhost" and settings.is_production():
        issues.append("Redis host should not be localhost in production")
    
    # Check trust scoring configuration
    if settings.trust_scoring.quarantine_threshold >= settings.trust_scoring.initial_trust_score:
        issues.append("Quarantine threshold should be less than initial trust score")
    
    # Check conflict prediction configuration
    if settings.conflict_prediction.risk_threshold <= 0 or settings.conflict_prediction.risk_threshold >= 1:
        issues.append("Conflict risk threshold must be between 0 and 1")
    
    # Check agent simulation configuration
    if settings.agent_simulation.min_agents > settings.agent_simulation.max_agents:
        issues.append("Minimum agents cannot be greater than maximum agents")

    # Check Kafka configuration for Confluent Cloud
    if settings.kafka.enabled:
        if "confluent" in settings.kafka.bootstrap_servers and not (settings.kafka.sasl_username and settings.kafka.sasl_password):
            issues.append("SASL credentials required for Confluent Cloud")
        if settings.kafka.security_protocol == "SASL_SSL" and not settings.kafka.sasl_mechanism:
            issues.append("SASL mechanism required when security protocol is SASL_SSL")
        
        # Production readiness checks
        if settings.is_production():
            if settings.kafka.security_protocol != "SASL_SSL":
                issues.append("Production deployments should use SASL_SSL for Kafka")
            if settings.kafka.buffer_size < 1000:
                issues.append("Kafka buffer size should be at least 1000 for production")
    
    # Performance optimization checks
    if settings.is_production():
        if settings.agent_simulation.max_agents > 100:
            issues.append("Consider horizontal scaling for >100 agents in production")
        if settings.trust_scoring.quarantine_threshold < 10:
            issues.append("Quarantine threshold may be too aggressive for production")
    
    return issues


# Global settings instance
settings = load_settings()

# Validate configuration on import
config_issues = validate_configuration(settings)
if config_issues:
    import warnings
    for issue in config_issues:
        warnings.warn(f"Configuration issue: {issue}", UserWarning)