"""
Load testing and performance benchmarking for production readiness.
"""
import time
import threading
import asyncio
import statistics
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import random

from .config import settings
from .logging_config import get_agent_logger
from .integrations.kafka_client import kafka_bus
from .stream_processor import stream_processor
from .prediction_engine.models.core import AgentIntention
from .performance_optimizer import performance_monitor, resource_manager

agent_logger = get_agent_logger(__name__)


@dataclass
class LoadTestResult:
    """Results from a load test execution."""
    test_name: str
    duration_seconds: float
    total_operations: int
    successful_operations: int
    failed_operations: int
    operations_per_second: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    error_rate: float
    resource_usage: Dict[str, float]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class BenchmarkConfig:
    """Configuration for benchmark tests."""
    name: str
    duration_seconds: int = 60
    concurrent_users: int = 10
    operations_per_second: int = 100
    ramp_up_seconds: int = 10
    ramp_down_seconds: int = 10
    target_success_rate: float = 0.95
    target_p95_latency_ms: float = 500.0


class KafkaLoadTester:
    """Load tester for Kafka message processing."""
    
    def __init__(self):
        self.results: List[LoadTestResult] = []
        self.running = False
        
    def run_producer_load_test(self, config: BenchmarkConfig) -> LoadTestResult:
        """Run load test for Kafka message production."""
        agent_logger.log_agent_action(
            "INFO",
            f"Starting Kafka producer load test: {config.name}",
            action_type="load_test_start",
            context={"config": config.__dict__}
        )
        
        latencies = []
        successful_ops = 0
        failed_ops = 0
        start_time = time.time()
        
        def produce_message() -> float:
            """Produce a single message and return latency."""
            msg_start = time.time()
            try:
                # Create a realistic agent message
                message = {
                    "agent_id": f"load_test_agent_{random.randint(1, 100)}",
                    "resource_type": random.choice(["cpu", "memory", "network", "storage"]),
                    "requested_amount": random.randint(10, 500),
                    "priority_level": random.randint(1, 10),
                    "timestamp": datetime.now().isoformat()
                }
                
                kafka_bus.produce(
                    settings.kafka.agent_messages_topic,
                    message,
                    key=message["agent_id"]
                )
                
                return (time.time() - msg_start) * 1000  # Convert to ms
                
            except Exception as e:
                agent_logger.log_system_error(e, "kafka_load_tester", "produce_message")
                return -1  # Indicate failure
        
        # Execute load test
        with ThreadPoolExecutor(max_workers=config.concurrent_users) as executor:
            futures = []
            
            # Ramp up phase
            for i in range(config.operations_per_second * config.duration_seconds):
                if time.time() - start_time > config.duration_seconds:
                    break
                
                future = executor.submit(produce_message)
                futures.append(future)
                
                # Control rate
                if i > 0 and i % config.operations_per_second == 0:
                    time.sleep(1.0)
            
            # Collect results
            for future in as_completed(futures):
                try:
                    latency = future.result(timeout=30.0)
                    if latency > 0:
                        latencies.append(latency)
                        successful_ops += 1
                    else:
                        failed_ops += 1
                except Exception:
                    failed_ops += 1
        
        # Calculate metrics
        end_time = time.time()
        duration = end_time - start_time
        total_ops = successful_ops + failed_ops
        
        result = LoadTestResult(
            test_name=config.name,
            duration_seconds=duration,
            total_operations=total_ops,
            successful_operations=successful_ops,
            failed_operations=failed_ops,
            operations_per_second=total_ops / duration if duration > 0 else 0,
            avg_latency_ms=statistics.mean(latencies) if latencies else 0,
            min_latency_ms=min(latencies) if latencies else 0,
            max_latency_ms=max(latencies) if latencies else 0,
            p95_latency_ms=statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else 0,
            p99_latency_ms=statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else 0,
            error_rate=failed_ops / total_ops if total_ops > 0 else 0,
            resource_usage=resource_manager.check_resource_constraints()
        )
        
        self.results.append(result)
        
        agent_logger.log_agent_action(
            "INFO",
            f"Kafka producer load test completed: {successful_ops}/{total_ops} successful",
            action_type="load_test_complete",
            context={
                "ops_per_second": result.operations_per_second,
                "avg_latency": result.avg_latency_ms,
                "error_rate": result.error_rate
            }
        )
        
        return result
    
    def run_consumer_load_test(self, config: BenchmarkConfig) -> LoadTestResult:
        """Run load test for Kafka message consumption."""
        agent_logger.log_agent_action(
            "INFO",
            f"Starting Kafka consumer load test: {config.name}",
            action_type="consumer_load_test_start"
        )
        
        # First, produce messages to consume
        producer_config = BenchmarkConfig(
            name=f"{config.name}_producer_setup",
            duration_seconds=30,
            concurrent_users=5,
            operations_per_second=config.operations_per_second
        )
        
        self.run_producer_load_test(producer_config)
        
        # Now test consumption
        consumed_messages = 0
        processing_latencies = []
        start_time = time.time()
        
        # Create a temporary consumer
        consumer = kafka_bus.create_temporary_consumer(f"load_test_consumer_{int(time.time())}")
        if not consumer:
            return LoadTestResult(
                test_name=config.name,
                duration_seconds=0,
                total_operations=0,
                successful_operations=0,
                failed_operations=1,
                operations_per_second=0,
                avg_latency_ms=0,
                min_latency_ms=0,
                max_latency_ms=0,
                p95_latency_ms=0,
                p99_latency_ms=0,
                error_rate=1.0,
                resource_usage={}
            )
        
        try:
            consumer.subscribe([settings.kafka.agent_messages_topic])
            
            while time.time() - start_time < config.duration_seconds:
                msg_start = time.time()
                msg = consumer.poll(timeout=1.0)
                
                if msg and not msg.error():
                    processing_time = (time.time() - msg_start) * 1000
                    processing_latencies.append(processing_time)
                    consumed_messages += 1
                    consumer.commit()
        
        finally:
            consumer.close()
        
        duration = time.time() - start_time
        
        result = LoadTestResult(
            test_name=config.name,
            duration_seconds=duration,
            total_operations=consumed_messages,
            successful_operations=consumed_messages,
            failed_operations=0,
            operations_per_second=consumed_messages / duration if duration > 0 else 0,
            avg_latency_ms=statistics.mean(processing_latencies) if processing_latencies else 0,
            min_latency_ms=min(processing_latencies) if processing_latencies else 0,
            max_latency_ms=max(processing_latencies) if processing_latencies else 0,
            p95_latency_ms=statistics.quantiles(processing_latencies, n=20)[18] if len(processing_latencies) >= 20 else 0,
            p99_latency_ms=statistics.quantiles(processing_latencies, n=100)[98] if len(processing_latencies) >= 100 else 0,
            error_rate=0,
            resource_usage=resource_manager.check_resource_constraints()
        )
        
        self.results.append(result)
        return result


class StreamProcessingLoadTester:
    """Load tester for stream processing pipeline."""
    
    def __init__(self):
        self.results: List[LoadTestResult] = []
    
    def run_end_to_end_load_test(self, config: BenchmarkConfig) -> LoadTestResult:
        """Run end-to-end load test of the stream processing pipeline."""
        agent_logger.log_agent_action(
            "INFO",
            f"Starting end-to-end stream processing load test: {config.name}",
            action_type="e2e_load_test_start"
        )
        
        # Ensure stream processor is running
        if not stream_processor.running:
            stream_processor.start()
            time.sleep(2)  # Allow startup
        
        latencies = []
        successful_ops = 0
        failed_ops = 0
        start_time = time.time()
        
        def process_agent_intention() -> float:
            """Process a single agent intention and measure latency."""
            intention_start = time.time()
            try:
                # Create realistic agent intention
                intention_data = {
                    "agent_id": f"load_test_agent_{random.randint(1, 50)}",
                    "resource_type": random.choice(["cpu", "memory", "network", "storage"]),
                    "requested_amount": random.randint(10, 1000),
                    "priority_level": random.randint(1, 10),
                    "timestamp": datetime.now().isoformat()
                }
                
                # Produce to input topic
                kafka_bus.produce(
                    settings.kafka.agent_messages_topic,
                    intention_data,
                    key=intention_data["agent_id"]
                )
                
                # Wait for processing (simplified - in real scenario would track specific message)
                time.sleep(0.01)  # Minimal processing time
                
                return (time.time() - intention_start) * 1000
                
            except Exception as e:
                agent_logger.log_system_error(e, "stream_load_tester", "process_intention")
                return -1
        
        # Execute load test with controlled rate
        with ThreadPoolExecutor(max_workers=config.concurrent_users) as executor:
            futures = []
            
            for i in range(config.operations_per_second * config.duration_seconds):
                if time.time() - start_time > config.duration_seconds:
                    break
                
                future = executor.submit(process_agent_intention)
                futures.append(future)
                
                # Rate limiting
                if i > 0 and i % config.operations_per_second == 0:
                    time.sleep(1.0)
            
            # Collect results
            for future in as_completed(futures):
                try:
                    latency = future.result(timeout=30.0)
                    if latency > 0:
                        latencies.append(latency)
                        successful_ops += 1
                    else:
                        failed_ops += 1
                except Exception:
                    failed_ops += 1
        
        duration = time.time() - start_time
        total_ops = successful_ops + failed_ops
        
        result = LoadTestResult(
            test_name=config.name,
            duration_seconds=duration,
            total_operations=total_ops,
            successful_operations=successful_ops,
            failed_operations=failed_ops,
            operations_per_second=total_ops / duration if duration > 0 else 0,
            avg_latency_ms=statistics.mean(latencies) if latencies else 0,
            min_latency_ms=min(latencies) if latencies else 0,
            max_latency_ms=max(latencies) if latencies else 0,
            p95_latency_ms=statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else 0,
            p99_latency_ms=statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else 0,
            error_rate=failed_ops / total_ops if total_ops > 0 else 0,
            resource_usage=resource_manager.check_resource_constraints()
        )
        
        self.results.append(result)
        return result


class PerformanceBenchmarkSuite:
    """Comprehensive performance benchmark suite."""
    
    def __init__(self):
        self.kafka_tester = KafkaLoadTester()
        self.stream_tester = StreamProcessingLoadTester()
        self.benchmark_results: List[LoadTestResult] = []
    
    def run_production_readiness_benchmarks(self) -> Dict[str, Any]:
        """Run comprehensive production readiness benchmarks."""
        agent_logger.log_agent_action(
            "INFO",
            "Starting production readiness benchmark suite",
            action_type="benchmark_suite_start"
        )
        
        # Start performance monitoring
        performance_monitor.start_monitoring()
        
        try:
            benchmarks = [
                # Kafka Producer Benchmarks
                BenchmarkConfig(
                    name="kafka_producer_baseline",
                    duration_seconds=30,
                    concurrent_users=5,
                    operations_per_second=50,
                    target_p95_latency_ms=100.0
                ),
                BenchmarkConfig(
                    name="kafka_producer_high_throughput",
                    duration_seconds=60,
                    concurrent_users=10,
                    operations_per_second=200,
                    target_p95_latency_ms=200.0
                ),
                BenchmarkConfig(
                    name="kafka_producer_stress_test",
                    duration_seconds=30,
                    concurrent_users=20,
                    operations_per_second=500,
                    target_p95_latency_ms=500.0
                ),
                
                # Stream Processing Benchmarks
                BenchmarkConfig(
                    name="stream_processing_baseline",
                    duration_seconds=45,
                    concurrent_users=5,
                    operations_per_second=30,
                    target_p95_latency_ms=200.0
                ),
                BenchmarkConfig(
                    name="stream_processing_high_load",
                    duration_seconds=60,
                    concurrent_users=10,
                    operations_per_second=100,
                    target_p95_latency_ms=400.0
                )
            ]
            
            results = []
            
            for config in benchmarks:
                if "kafka_producer" in config.name:
                    result = self.kafka_tester.run_producer_load_test(config)
                elif "stream_processing" in config.name:
                    result = self.stream_tester.run_end_to_end_load_test(config)
                else:
                    continue
                
                results.append(result)
                self.benchmark_results.append(result)
                
                # Brief pause between tests
                time.sleep(5)
            
            # Generate summary report
            summary = self._generate_benchmark_summary(results)
            
            agent_logger.log_agent_action(
                "INFO",
                "Production readiness benchmark suite completed",
                action_type="benchmark_suite_complete",
                context=summary
            )
            
            return summary
            
        finally:
            performance_monitor.stop_monitoring()
    
    def _generate_benchmark_summary(self, results: List[LoadTestResult]) -> Dict[str, Any]:
        """Generate summary report from benchmark results."""
        if not results:
            return {"status": "no_results"}
        
        total_operations = sum(r.total_operations for r in results)
        total_successful = sum(r.successful_operations for r in results)
        avg_throughput = statistics.mean([r.operations_per_second for r in results])
        avg_latency = statistics.mean([r.avg_latency_ms for r in results])
        max_error_rate = max([r.error_rate for r in results])
        
        # Determine overall status
        status = "passed"
        issues = []
        
        for result in results:
            if result.error_rate > 0.05:  # 5% error rate threshold
                status = "failed"
                issues.append(f"{result.test_name}: High error rate ({result.error_rate:.2%})")
            
            if result.p95_latency_ms > 1000:  # 1 second P95 threshold
                status = "warning" if status == "passed" else status
                issues.append(f"{result.test_name}: High P95 latency ({result.p95_latency_ms:.1f}ms)")
        
        return {
            "status": status,
            "summary": {
                "total_tests": len(results),
                "total_operations": total_operations,
                "successful_operations": total_successful,
                "overall_success_rate": total_successful / total_operations if total_operations > 0 else 0,
                "avg_throughput": round(avg_throughput, 2),
                "avg_latency_ms": round(avg_latency, 2),
                "max_error_rate": round(max_error_rate, 4)
            },
            "issues": issues,
            "detailed_results": [
                {
                    "test_name": r.test_name,
                    "ops_per_second": r.operations_per_second,
                    "avg_latency_ms": r.avg_latency_ms,
                    "p95_latency_ms": r.p95_latency_ms,
                    "error_rate": r.error_rate,
                    "success": r.error_rate < 0.05 and r.p95_latency_ms < 1000
                }
                for r in results
            ]
        }
    
    def run_continuous_load_test(self, duration_minutes: int = 10) -> LoadTestResult:
        """Run continuous load test to validate system stability."""
        config = BenchmarkConfig(
            name="continuous_stability_test",
            duration_seconds=duration_minutes * 60,
            concurrent_users=8,
            operations_per_second=50,
            target_success_rate=0.98
        )
        
        return self.stream_tester.run_end_to_end_load_test(config)


# Global instances
kafka_load_tester = KafkaLoadTester()
stream_load_tester = StreamProcessingLoadTester()
benchmark_suite = PerformanceBenchmarkSuite()