"""
Production readiness validation and optimization suite.
"""
import time
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime

from .config import settings, validate_configuration
from .config_validator import ConfigurationValidator
from .performance_optimizer import (
    kafka_optimizer, 
    connection_pool_manager, 
    performance_monitor, 
    resource_manager
)
from .load_testing import benchmark_suite
from .stream_monitoring import stream_monitor, stream_dashboard
from .logging_config import get_agent_logger

agent_logger = get_agent_logger(__name__)


class ProductionReadinessValidator:
    """Validates system readiness for production deployment."""
    
    def __init__(self):
        self.validation_results: Dict[str, Any] = {}
        self.start_time = datetime.now()
    
    def run_full_validation(self) -> Dict[str, Any]:
        """Run comprehensive production readiness validation."""
        agent_logger.log_agent_action(
            "INFO",
            "Starting production readiness validation",
            action_type="production_validation_start"
        )
        
        self.validation_results = {
            "overall_status": "unknown",
            "validation_timestamp": self.start_time.isoformat(),
            "environment": settings.environment.value,
            "checks": {}
        }
        
        # Run validation checks
        checks = [
            ("configuration", self._validate_configuration),
            ("kafka_optimization", self._validate_kafka_optimization),
            ("resource_management", self._validate_resource_management),
            ("performance_benchmarks", self._validate_performance_benchmarks),
            ("monitoring_setup", self._validate_monitoring_setup),
            ("security_configuration", self._validate_security_configuration),
            ("scalability_readiness", self._validate_scalability_readiness)
        ]
        
        passed_checks = 0
        total_checks = len(checks)
        
        for check_name, check_function in checks:
            try:
                result = check_function()
                self.validation_results["checks"][check_name] = result
                if result.get("status") == "passed":
                    passed_checks += 1
            except Exception as e:
                agent_logger.log_system_error(e, "production_validator", check_name)
                self.validation_results["checks"][check_name] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        # Determine overall status
        success_rate = passed_checks / total_checks
        if success_rate >= 0.9:
            self.validation_results["overall_status"] = "ready"
        elif success_rate >= 0.7:
            self.validation_results["overall_status"] = "needs_attention"
        else:
            self.validation_results["overall_status"] = "not_ready"
        
        self.validation_results["summary"] = {
            "passed_checks": passed_checks,
            "total_checks": total_checks,
            "success_rate": success_rate,
            "duration_seconds": (datetime.now() - self.start_time).total_seconds()
        }
        
        agent_logger.log_agent_action(
            "INFO",
            f"Production readiness validation completed: {self.validation_results['overall_status']}",
            action_type="production_validation_complete",
            context=self.validation_results["summary"]
        )
        
        return self.validation_results
    
    def _validate_configuration(self) -> Dict[str, Any]:
        """Validate system configuration for production."""
        try:
            validator = ConfigurationValidator(settings)
            results = validator.validate_all()
            
            # Additional production-specific checks
            production_issues = []
            
            if settings.environment.value != "production":
                production_issues.append("Environment is not set to production")
            
            if settings.debug:
                production_issues.append("Debug mode is enabled in production")
            
            # Check Confluent Cloud configuration
            kafka_issues = kafka_optimizer.validate_confluent_cloud_config()
            production_issues.extend(kafka_issues)
            
            # Check required integrations are enabled
            if not settings.kafka.enabled:
                production_issues.append("Kafka integration is disabled")
            
            if not settings.datadog.enabled and settings.environment.value == "production":
                production_issues.append("Datadog monitoring should be enabled in production")
            
            status = "failed" if results["issues"] or production_issues else "passed"
            
            return {
                "status": status,
                "configuration_issues": results["issues"],
                "production_issues": production_issues,
                "warnings": results["warnings"],
                "component_status": results["component_status"]
            }
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _validate_kafka_optimization(self) -> Dict[str, Any]:
        """Validate Kafka optimization and configuration."""
        try:
            issues = []
            
            # Check if Kafka is enabled
            if not settings.kafka.enabled:
                return {"status": "skipped", "reason": "Kafka is disabled"}
            
            # Validate Confluent Cloud configuration
            confluent_issues = kafka_optimizer.validate_confluent_cloud_config()
            issues.extend(confluent_issues)
            
            # Check optimized configurations
            producer_config = kafka_optimizer.get_optimized_producer_config()
            consumer_config = kafka_optimizer.get_optimized_consumer_config("test-group")
            
            # Validate key production settings
            if producer_config.get('acks') != 'all':
                issues.append("Producer should use 'acks=all' for production reliability")
            
            if not producer_config.get('enable.idempotence'):
                issues.append("Producer should enable idempotence for production")
            
            if consumer_config.get('enable.auto.commit', True):
                issues.append("Consumer should use manual commits for production reliability")
            
            # Test basic connectivity (if possible)
            connectivity_test = self._test_kafka_connectivity()
            
            status = "failed" if issues else "passed"
            
            return {
                "status": status,
                "issues": issues,
                "connectivity": connectivity_test,
                "producer_config_keys": list(producer_config.keys()),
                "consumer_config_keys": list(consumer_config.keys())
            }
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _test_kafka_connectivity(self) -> Dict[str, Any]:
        """Test basic Kafka connectivity."""
        try:
            # Test buffer status (basic connectivity check)
            buffer_status = kafka_bus.get_buffer_status()
            
            return {
                "connected": buffer_status.get('is_connected', False),
                "buffer_size": buffer_status.get('size', 0),
                "test_timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}
    
    def _validate_resource_management(self) -> Dict[str, Any]:
        """Validate resource management and optimization."""
        try:
            # Check resource constraints
            resource_status = resource_manager.check_resource_constraints()
            
            # Check connection pool setup
            thread_pool = connection_pool_manager.get_thread_pool()
            
            issues = []
            if not resource_status.get('overall_ok', False):
                issues.append("Resource constraints are not met")
            
            if thread_pool._max_workers < 4:
                issues.append("Thread pool size may be too small for production")
            
            status = "failed" if issues else "passed"
            
            return {
                "status": status,
                "issues": issues,
                "resource_status": resource_status,
                "thread_pool_workers": thread_pool._max_workers
            }
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _validate_performance_benchmarks(self) -> Dict[str, Any]:
        """Run performance benchmarks to validate production readiness."""
        try:
            # Run a subset of benchmarks for validation
            from .load_testing import BenchmarkConfig, kafka_load_tester
            
            # Quick producer test
            quick_config = BenchmarkConfig(
                name="production_validation_test",
                duration_seconds=15,
                concurrent_users=3,
                operations_per_second=20,
                target_p95_latency_ms=200.0
            )
            
            if settings.kafka.enabled:
                result = kafka_load_tester.run_producer_load_test(quick_config)
                
                issues = []
                if result.error_rate > 0.05:
                    issues.append(f"High error rate in benchmark: {result.error_rate:.2%}")
                
                if result.p95_latency_ms > 500:
                    issues.append(f"High P95 latency in benchmark: {result.p95_latency_ms:.1f}ms")
                
                status = "failed" if issues else "passed"
                
                return {
                    "status": status,
                    "issues": issues,
                    "benchmark_result": {
                        "ops_per_second": result.operations_per_second,
                        "avg_latency_ms": result.avg_latency_ms,
                        "p95_latency_ms": result.p95_latency_ms,
                        "error_rate": result.error_rate
                    }
                }
            else:
                return {"status": "skipped", "reason": "Kafka is disabled"}
                
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _validate_monitoring_setup(self) -> Dict[str, Any]:
        """Validate monitoring and alerting setup."""
        try:
            issues = []
            
            # Check if monitoring components are available
            monitoring_components = {
                "stream_monitor": stream_monitor,
                "performance_monitor": performance_monitor,
                "stream_dashboard": stream_dashboard
            }
            
            for component_name, component in monitoring_components.items():
                if component is None:
                    issues.append(f"{component_name} is not available")
            
            # Check Datadog integration for production
            if settings.environment.value == "production" and not settings.datadog.enabled:
                issues.append("Datadog monitoring should be enabled in production")
            
            # Test monitoring functionality
            try:
                # Start stream monitoring briefly
                stream_monitor.start_monitoring()
                time.sleep(2)
                
                current_metrics = stream_monitor.get_current_metrics()
                if current_metrics is None:
                    issues.append("Stream monitoring is not collecting metrics")
                
                stream_monitor.stop_monitoring()
                
            except Exception as e:
                issues.append(f"Stream monitoring test failed: {str(e)}")
            
            status = "failed" if issues else "passed"
            
            return {
                "status": status,
                "issues": issues,
                "datadog_enabled": settings.datadog.enabled,
                "monitoring_components": list(monitoring_components.keys())
            }
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _validate_security_configuration(self) -> Dict[str, Any]:
        """Validate security configuration for production."""
        try:
            issues = []
            
            # Check Kafka security
            if settings.kafka.enabled:
                if settings.kafka.security_protocol != "SASL_SSL":
                    issues.append("Kafka should use SASL_SSL in production")
                
                if not settings.kafka.sasl_username or not settings.kafka.sasl_password:
                    issues.append("Kafka SASL credentials are missing")
            
            # Check API keys are not default values
            if settings.gemini.api_key in ["", "your_gemini_api_key_here"]:
                issues.append("Gemini API key is not configured")
            
            if settings.datadog.enabled:
                if settings.datadog.api_key in ["", "your_datadog_api_key_here"]:
                    issues.append("Datadog API key is not configured")
            
            # Check Redis security (basic)
            if settings.redis.password is None and settings.environment.value == "production":
                issues.append("Redis password should be set in production")
            
            status = "failed" if issues else "passed"
            
            return {
                "status": status,
                "issues": issues,
                "kafka_security_protocol": settings.kafka.security_protocol,
                "redis_password_set": settings.redis.password is not None
            }
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _validate_scalability_readiness(self) -> Dict[str, Any]:
        """Validate system readiness for scaling."""
        try:
            issues = []
            recommendations = []
            
            # Check agent simulation limits
            if settings.agent_simulation.max_agents > 50:
                recommendations.append("Consider horizontal scaling for >50 agents")
            
            # Check resource limits
            resource_status = resource_manager.check_resource_constraints()
            if resource_status.get('memory', {}).get('usage', 0) > 70:
                recommendations.append("Memory usage is high, consider scaling")
            
            # Check Kafka partitioning strategy
            if settings.kafka.enabled:
                # In a real implementation, would check topic partition counts
                recommendations.append("Ensure Kafka topics have adequate partitions for scaling")
            
            # Check connection pool sizing
            thread_pool = connection_pool_manager.get_thread_pool()
            if thread_pool._max_workers < 16:
                recommendations.append("Consider increasing thread pool size for higher loads")
            
            status = "passed"  # Scalability is more about recommendations
            
            return {
                "status": status,
                "issues": issues,
                "recommendations": recommendations,
                "current_max_agents": settings.agent_simulation.max_agents,
                "thread_pool_size": thread_pool._max_workers
            }
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def print_validation_report(self):
        """Print a formatted validation report."""
        if not self.validation_results:
            print("No validation results available. Run validation first.")
            return
        
        print("\n" + "=" * 80)
        print("CHORUS AGENT CONFLICT PREDICTOR - PRODUCTION READINESS REPORT")
        print("=" * 80)
        
        # Overall status
        overall_status = self.validation_results["overall_status"]
        status_colors = {
            "ready": "\033[92m",      # Green
            "needs_attention": "\033[93m",  # Yellow
            "not_ready": "\033[91m",  # Red
        }
        reset_color = "\033[0m"
        
        print(f"\nOverall Status: {status_colors.get(overall_status, '')}{overall_status.upper()}{reset_color}")
        print(f"Environment: {self.validation_results['environment']}")
        print(f"Validation Time: {self.validation_results['validation_timestamp']}")
        
        # Summary
        summary = self.validation_results["summary"]
        print(f"\nSummary: {summary['passed_checks']}/{summary['total_checks']} checks passed")
        print(f"Success Rate: {summary['success_rate']:.1%}")
        print(f"Duration: {summary['duration_seconds']:.1f} seconds")
        
        # Detailed results
        print(f"\nDetailed Results:")
        for check_name, result in self.validation_results["checks"].items():
            status = result.get("status", "unknown")
            status_symbol = {"passed": "✓", "failed": "✗", "skipped": "-"}.get(status, "?")
            print(f"  {status_symbol} {check_name}: {status}")
            
            # Show issues if any
            if result.get("issues"):
                for issue in result["issues"]:
                    print(f"    • {issue}")
            
            # Show recommendations if any
            if result.get("recommendations"):
                for rec in result["recommendations"]:
                    print(f"    → {rec}")
        
        print("\n" + "=" * 80)


def run_production_readiness_check() -> int:
    """
    CLI function to run production readiness validation.
    
    Returns:
        Exit code (0 for ready, 1 for needs attention, 2 for not ready)
    """
    try:
        validator = ProductionReadinessValidator()
        results = validator.run_full_validation()
        validator.print_validation_report()
        
        status = results["overall_status"]
        if status == "ready":
            return 0
        elif status == "needs_attention":
            return 1
        else:
            return 2
            
    except Exception as e:
        print(f"\nProduction readiness validation failed: {str(e)}")
        return 2


if __name__ == "__main__":
    exit_code = run_production_readiness_check()
    sys.exit(exit_code)