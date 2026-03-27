"""
Configuration validation utilities for the Chorus Agent Conflict Predictor.
"""
import sys
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    from .config import Settings, validate_configuration, load_settings
    from .logging_config import get_agent_logger
except ImportError:
    # Handle direct execution
    from config import Settings, validate_configuration, load_settings
    from logging_config import get_agent_logger

agent_logger = get_agent_logger(__name__)


class ConfigurationValidator:
    """Validates system configuration and dependencies."""
    
    def __init__(self, settings: Settings):
        """
        Initialize the configuration validator.
        
        Args:
            settings: Settings instance to validate
        """
        self.settings = settings
        self.validation_results: Dict[str, Any] = {}
    
    def validate_all(self) -> Dict[str, Any]:
        """
        Run all configuration validations.
        
        Returns:
            Dictionary containing validation results
        """
        self.validation_results = {
            "overall_status": "unknown",
            "issues": [],
            "warnings": [],
            "component_status": {},
            "environment_info": self._get_environment_info()
        }
        
        # Run individual validations
        self._validate_basic_config()
        self._validate_gemini_config()
        self._validate_redis_config()
        self._validate_optional_integrations()
        self._validate_thresholds_and_policies()
        self._validate_logging_config()
        
        # Determine overall status
        if self.validation_results["issues"]:
            self.validation_results["overall_status"] = "failed"
        elif self.validation_results["warnings"]:
            self.validation_results["overall_status"] = "warning"
        else:
            self.validation_results["overall_status"] = "passed"
        
        return self.validation_results
    
    def _get_environment_info(self) -> Dict[str, Any]:
        """Get environment information."""
        return {
            "environment": self.settings.environment.value,
            "debug": self.settings.debug,
            "python_version": sys.version,
            "config_file": ".env" if Path(".env").exists() else "environment variables"
        }
    
    def _validate_basic_config(self) -> None:
        """Validate basic configuration settings."""
        component = "basic_config"
        
        try:
            # Use the built-in validation
            issues = validate_configuration(self.settings)
            
            if issues:
                self.validation_results["issues"].extend(issues)
                self.validation_results["component_status"][component] = "failed"
            else:
                self.validation_results["component_status"][component] = "passed"
                
        except Exception as e:
            self.validation_results["issues"].append(f"Basic configuration validation failed: {str(e)}")
            self.validation_results["component_status"][component] = "failed"
    
    def _validate_gemini_config(self) -> None:
        """Validate Gemini API configuration."""
        component = "gemini_api"
        
        try:
            if not self.settings.gemini.api_key:
                self.validation_results["issues"].append("Gemini API key is required")
                self.validation_results["component_status"][component] = "failed"
                return
            
            if self.settings.gemini.api_key == "your_gemini_api_key_here":
                self.validation_results["issues"].append("Gemini API key appears to be placeholder value")
                self.validation_results["component_status"][component] = "failed"
                return
            
            # Test API connection (optional, can be slow)
            if self.settings.environment.value in ["development", "testing"]:
                try:
                    from .prediction_engine.gemini_client import GeminiClient
                    client = GeminiClient()
                    if client.test_connection():
                        self.validation_results["component_status"][component] = "passed"
                    else:
                        self.validation_results["warnings"].append("Gemini API connection test failed")
                        self.validation_results["component_status"][component] = "warning"
                except ImportError:
                    self.validation_results["warnings"].append("Cannot test Gemini API connection (client not available)")
                    self.validation_results["component_status"][component] = "warning"
                except Exception as e:
                    self.validation_results["warnings"].append(f"Gemini API connection test error: {str(e)}")
                    self.validation_results["component_status"][component] = "warning"
            else:
                self.validation_results["component_status"][component] = "passed"
                
        except Exception as e:
            self.validation_results["issues"].append(f"Gemini configuration validation failed: {str(e)}")
            self.validation_results["component_status"][component] = "failed"
    
    def _validate_redis_config(self) -> None:
        """Validate Redis configuration."""
        component = "redis"
        
        try:
            # Basic configuration checks
            if self.settings.redis.port < 1 or self.settings.redis.port > 65535:
                self.validation_results["issues"].append("Redis port must be between 1 and 65535")
                self.validation_results["component_status"][component] = "failed"
                return
            
            if self.settings.redis.db < 0 or self.settings.redis.db > 15:
                self.validation_results["issues"].append("Redis database number must be between 0 and 15")
                self.validation_results["component_status"][component] = "failed"
                return
            
            # Production-specific checks
            if self.settings.is_production() and self.settings.redis.host == "localhost":
                self.validation_results["warnings"].append("Redis host is localhost in production environment")
                self.validation_results["component_status"][component] = "warning"
            
            # Test Redis connection (optional)
            if self.settings.environment.value in ["development", "testing"]:
                try:
                    from .prediction_engine.redis_client import RedisClient
                    client = RedisClient()
                    if client.ping():
                        self.validation_results["component_status"][component] = "passed"
                    else:
                        self.validation_results["warnings"].append("Redis connection test failed")
                        self.validation_results["component_status"][component] = "warning"
                except ImportError:
                    self.validation_results["warnings"].append("Cannot test Redis connection (client not available)")
                    self.validation_results["component_status"][component] = "warning"
                except Exception as e:
                    self.validation_results["warnings"].append(f"Redis connection test error: {str(e)}")
                    self.validation_results["component_status"][component] = "warning"
            else:
                self.validation_results["component_status"][component] = "passed"
                
        except Exception as e:
            self.validation_results["issues"].append(f"Redis configuration validation failed: {str(e)}")
            self.validation_results["component_status"][component] = "failed"
    
    def _validate_optional_integrations(self) -> None:
        """Validate optional integration configurations."""
        
        # Datadog validation
        if self.settings.datadog.enabled:
            component = "datadog"
            if not self.settings.datadog.api_key or not self.settings.datadog.app_key:
                self.validation_results["issues"].append("Datadog API key and app key are required when enabled")
                self.validation_results["component_status"][component] = "failed"
            elif (self.settings.datadog.api_key == "your_datadog_api_key_here" or 
                  self.settings.datadog.app_key == "your_datadog_app_key_here"):
                self.validation_results["issues"].append("Datadog keys appear to be placeholder values")
                self.validation_results["component_status"][component] = "failed"
            else:
                self.validation_results["component_status"][component] = "passed"
        else:
            self.validation_results["component_status"]["datadog"] = "disabled"
        
        # ElevenLabs validation
        if self.settings.elevenlabs.enabled:
            component = "elevenlabs"
            if not self.settings.elevenlabs.api_key:
                self.validation_results["issues"].append("ElevenLabs API key is required when enabled")
                self.validation_results["component_status"][component] = "failed"
            elif self.settings.elevenlabs.api_key == "your_elevenlabs_api_key_here":
                self.validation_results["issues"].append("ElevenLabs API key appears to be placeholder value")
                self.validation_results["component_status"][component] = "failed"
            else:
                self.validation_results["component_status"][component] = "passed"
        else:
            self.validation_results["component_status"]["elevenlabs"] = "disabled"
        
        # Kafka validation
        if self.settings.kafka.enabled:
            component = "kafka"
            if not self.settings.kafka.bootstrap_servers:
                self.validation_results["issues"].append("Kafka bootstrap servers are required when enabled")
                self.validation_results["component_status"][component] = "failed"
            else:
                self.validation_results["component_status"][component] = "passed"
        else:
            self.validation_results["component_status"]["kafka"] = "disabled"
    
    def _validate_thresholds_and_policies(self) -> None:
        """Validate thresholds and policy configurations."""
        component = "thresholds_policies"
        
        try:
            # Trust scoring validation
            if (self.settings.trust_scoring.quarantine_threshold >= 
                self.settings.trust_scoring.initial_trust_score):
                self.validation_results["warnings"].append(
                    "Quarantine threshold should be less than initial trust score"
                )
            
            if (self.settings.trust_scoring.conflict_penalty <= 0 or 
                self.settings.trust_scoring.conflict_penalty > 50):
                self.validation_results["warnings"].append(
                    "Conflict penalty should be between 1 and 50"
                )
            
            # Conflict prediction validation
            if (self.settings.conflict_prediction.risk_threshold <= 0.0 or 
                self.settings.conflict_prediction.risk_threshold >= 1.0):
                self.validation_results["issues"].append(
                    "Conflict risk threshold must be between 0.0 and 1.0"
                )
                self.validation_results["component_status"][component] = "failed"
                return
            
            # Agent simulation validation
            if (self.settings.agent_simulation.min_agents > 
                self.settings.agent_simulation.max_agents):
                self.validation_results["issues"].append(
                    "Minimum agents cannot be greater than maximum agents"
                )
                self.validation_results["component_status"][component] = "failed"
                return
            
            if self.settings.agent_simulation.max_agents > 20:
                self.validation_results["warnings"].append(
                    "Large number of agents may impact performance"
                )
            
            self.validation_results["component_status"][component] = "passed"
            
        except Exception as e:
            self.validation_results["issues"].append(f"Threshold validation failed: {str(e)}")
            self.validation_results["component_status"][component] = "failed"
    
    def _validate_logging_config(self) -> None:
        """Validate logging configuration."""
        component = "logging"
        
        try:
            # Check log file path if specified
            if self.settings.logging.file_path:
                log_path = Path(self.settings.logging.file_path)
                if not log_path.parent.exists():
                    self.validation_results["warnings"].append(
                        f"Log file directory does not exist: {log_path.parent}"
                    )
            
            # Check log file size limits
            if self.settings.logging.max_file_size < 1024:  # 1KB minimum
                self.validation_results["warnings"].append(
                    "Log file size limit is very small (< 1KB)"
                )
            
            self.validation_results["component_status"][component] = "passed"
            
        except Exception as e:
            self.validation_results["issues"].append(f"Logging configuration validation failed: {str(e)}")
            self.validation_results["component_status"][component] = "failed"
    
    def print_validation_report(self) -> None:
        """Print a formatted validation report."""
        results = self.validation_results
        
        print("\n" + "=" * 60)
        print("CHORUS AGENT CONFLICT PREDICTOR - CONFIGURATION VALIDATION")
        print("=" * 60)
        
        # Overall status
        status_color = {
            "passed": "\033[92m",  # Green
            "warning": "\033[93m", # Yellow
            "failed": "\033[91m",  # Red
            "unknown": "\033[94m"  # Blue
        }
        reset_color = "\033[0m"
        
        overall_status = results["overall_status"]
        print(f"\nOverall Status: {status_color.get(overall_status, '')}{overall_status.upper()}{reset_color}")
        
        # Environment info
        env_info = results["environment_info"]
        print(f"\nEnvironment: {env_info['environment']}")
        print(f"Debug Mode: {env_info['debug']}")
        print(f"Config Source: {env_info['config_file']}")
        
        # Component status
        print(f"\nComponent Status:")
        for component, status in results["component_status"].items():
            status_symbol = {
                "passed": "✓",
                "warning": "⚠",
                "failed": "✗",
                "disabled": "-"
            }
            print(f"  {status_symbol.get(status, '?')} {component}: {status}")
        
        # Issues
        if results["issues"]:
            print(f"\n{status_color['failed']}ISSUES (must be fixed):{reset_color}")
            for issue in results["issues"]:
                print(f"  ✗ {issue}")
        
        # Warnings
        if results["warnings"]:
            print(f"\n{status_color['warning']}WARNINGS (should be reviewed):{reset_color}")
            for warning in results["warnings"]:
                print(f"  ⚠ {warning}")
        
        if not results["issues"] and not results["warnings"]:
            print(f"\n{status_color['passed']}All configuration checks passed!{reset_color}")
        
        print("\n" + "=" * 60)


def validate_config_cli(env_file: Optional[str] = None) -> int:
    """
    CLI function to validate configuration.
    
    Args:
        env_file: Optional path to .env file
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Load settings
        if env_file:
            settings = load_settings(env_file)
            print(f"Loading configuration from: {env_file}")
        else:
            settings = load_settings()
            print("Loading configuration from environment variables and .env file")
        
        # Run validation
        validator = ConfigurationValidator(settings)
        results = validator.validate_all()
        
        # Print report
        validator.print_validation_report()
        
        # Return appropriate exit code
        if results["overall_status"] == "failed":
            return 1
        else:
            return 0
            
    except Exception as e:
        print(f"\nConfiguration validation failed with error: {str(e)}")
        return 1


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate Chorus Agent Conflict Predictor configuration")
    parser.add_argument("--env-file", help="Path to .env file to validate")
    
    args = parser.parse_args()
    exit_code = validate_config_cli(args.env_file)
    sys.exit(exit_code)