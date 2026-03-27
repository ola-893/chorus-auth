#!/usr/bin/env python3
"""
Performance benchmarking CLI for production readiness validation.
"""
import sys
import argparse
import json
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import settings, load_settings
from src.logging_config import get_agent_logger
from src.load_testing import benchmark_suite, BenchmarkConfig
from src.production_readiness import ProductionReadinessValidator
from src.performance_optimizer import kafka_optimizer, performance_monitor, resource_manager

agent_logger = get_agent_logger(__name__)


def run_kafka_benchmarks(args):
    """Run Kafka-specific performance benchmarks."""
    print("Running Kafka Performance Benchmarks...")
    print("=" * 50)
    
    if not settings.kafka.enabled:
        print("❌ Kafka is disabled. Enable Kafka to run benchmarks.")
        return False
    
    # Validate Kafka configuration first
    issues = kafka_optimizer.validate_confluent_cloud_config()
    if issues:
        print("⚠️  Kafka Configuration Issues:")
        for issue in issues:
            print(f"   • {issue}")
        print()
    
    # Run benchmarks
    configs = [
        BenchmarkConfig(
            name="kafka_producer_baseline",
            duration_seconds=args.duration,
            concurrent_users=args.users,
            operations_per_second=args.rate,
            target_p95_latency_ms=200.0
        ),
        BenchmarkConfig(
            name="kafka_producer_stress",
            duration_seconds=args.duration // 2,
            concurrent_users=args.users * 2,
            operations_per_second=args.rate * 2,
            target_p95_latency_ms=500.0
        )
    ]
    
    results = []
    for config in configs:
        print(f"Running: {config.name}")
        print(f"  Duration: {config.duration_seconds}s")
        print(f"  Users: {config.concurrent_users}")
        print(f"  Rate: {config.operations_per_second} ops/s")
        
        from src.load_testing import kafka_load_tester
        result = kafka_load_tester.run_producer_load_test(config)
        results.append(result)
        
        # Print results
        print(f"  ✓ Completed: {result.operations_per_second:.1f} ops/s")
        print(f"    Latency: avg={result.avg_latency_ms:.1f}ms, p95={result.p95_latency_ms:.1f}ms")
        print(f"    Error Rate: {result.error_rate:.2%}")
        print()
    
    # Summary
    print("Kafka Benchmark Summary:")
    for result in results:
        status = "✓ PASS" if result.error_rate < 0.05 and result.p95_latency_ms < 1000 else "❌ FAIL"
        print(f"  {status} {result.test_name}: {result.operations_per_second:.1f} ops/s")
    
    return all(r.error_rate < 0.05 and r.p95_latency_ms < 1000 for r in results)


def run_stream_benchmarks(args):
    """Run stream processing benchmarks."""
    print("Running Stream Processing Benchmarks...")
    print("=" * 50)
    
    from src.load_testing import stream_load_tester
    
    config = BenchmarkConfig(
        name="stream_processing_benchmark",
        duration_seconds=args.duration,
        concurrent_users=args.users,
        operations_per_second=args.rate,
        target_p95_latency_ms=400.0
    )
    
    print(f"Running end-to-end stream processing test...")
    print(f"  Duration: {config.duration_seconds}s")
    print(f"  Users: {config.concurrent_users}")
    print(f"  Rate: {config.operations_per_second} ops/s")
    
    result = stream_load_tester.run_end_to_end_load_test(config)
    
    print(f"  ✓ Completed: {result.operations_per_second:.1f} ops/s")
    print(f"    Latency: avg={result.avg_latency_ms:.1f}ms, p95={result.p95_latency_ms:.1f}ms")
    print(f"    Error Rate: {result.error_rate:.2%}")
    
    status = "✓ PASS" if result.error_rate < 0.05 and result.p95_latency_ms < 1000 else "❌ FAIL"
    print(f"  {status} Stream Processing Benchmark")
    
    return result.error_rate < 0.05 and result.p95_latency_ms < 1000


def run_full_benchmark_suite(args):
    """Run the complete benchmark suite."""
    print("Running Full Production Readiness Benchmark Suite...")
    print("=" * 60)
    
    # Start performance monitoring
    performance_monitor.start_monitoring()
    
    try:
        results = benchmark_suite.run_production_readiness_benchmarks()
        
        print("\nBenchmark Suite Results:")
        print("=" * 30)
        
        summary = results.get("summary", {})
        print(f"Status: {results.get('status', 'unknown').upper()}")
        print(f"Total Tests: {summary.get('total_tests', 0)}")
        print(f"Success Rate: {summary.get('overall_success_rate', 0):.1%}")
        print(f"Avg Throughput: {summary.get('avg_throughput', 0):.1f} ops/s")
        print(f"Avg Latency: {summary.get('avg_latency_ms', 0):.1f}ms")
        
        if results.get("issues"):
            print("\nIssues Found:")
            for issue in results["issues"]:
                print(f"  ❌ {issue}")
        
        print("\nDetailed Results:")
        for test_result in results.get("detailed_results", []):
            status = "✓" if test_result.get("success", False) else "❌"
            print(f"  {status} {test_result['test_name']}: {test_result['ops_per_second']:.1f} ops/s")
        
        # Save results to file if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\nResults saved to: {args.output}")
        
        return results.get("status") == "passed"
        
    finally:
        performance_monitor.stop_monitoring()


def run_production_readiness_check(args):
    """Run production readiness validation."""
    print("Running Production Readiness Validation...")
    print("=" * 50)
    
    validator = ProductionReadinessValidator()
    results = validator.run_full_validation()
    validator.print_validation_report()
    
    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to: {args.output}")
    
    return results["overall_status"] in ["ready", "needs_attention"]


def run_resource_monitoring(args):
    """Run resource monitoring and optimization."""
    print("Running Resource Monitoring...")
    print("=" * 40)
    
    # Check current resource status
    resource_status = resource_manager.check_resource_constraints()
    
    print("Current Resource Status:")
    for resource, status in resource_status.items():
        if isinstance(status, dict):
            usage = status.get('usage', 0)
            ok = status.get('ok', True)
            status_symbol = "✓" if ok else "⚠️"
            print(f"  {status_symbol} {resource}: {usage}")
        else:
            print(f"  • {resource}: {status}")
    
    # Start performance monitoring for specified duration
    print(f"\nMonitoring performance for {args.duration} seconds...")
    
    performance_monitor.start_monitoring()
    
    try:
        import time
        time.sleep(args.duration)
        
        # Get performance summary
        summary = performance_monitor.get_performance_summary()
        
        print("\nPerformance Summary:")
        if summary.get("status") == "healthy":
            print("  ✓ System performance is healthy")
        else:
            print("  ⚠️ System performance needs attention")
        
        metrics = summary.get("metrics", {})
        for metric, value in metrics.items():
            print(f"    {metric}: {value}")
        
        recommendations = summary.get("recommendations", [])
        if recommendations:
            print("\nRecommendations:")
            for rec in recommendations:
                print(f"  • {rec}")
        
        return summary.get("status") == "healthy"
        
    finally:
        performance_monitor.stop_monitoring()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Chorus Agent Conflict Predictor Performance Benchmarking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python performance_benchmark.py kafka --duration 60 --users 10 --rate 100
  python performance_benchmark.py stream --duration 30 --users 5 --rate 50
  python performance_benchmark.py full --output results.json
  python performance_benchmark.py readiness --output readiness.json
  python performance_benchmark.py monitor --duration 120
        """
    )
    
    parser.add_argument("--env-file", help="Path to .env file")
    parser.add_argument("--output", help="Output file for results (JSON)")
    
    subparsers = parser.add_subparsers(dest="command", help="Benchmark commands")
    
    # Kafka benchmarks
    kafka_parser = subparsers.add_parser("kafka", help="Run Kafka performance benchmarks")
    kafka_parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    kafka_parser.add_argument("--users", type=int, default=10, help="Concurrent users")
    kafka_parser.add_argument("--rate", type=int, default=100, help="Operations per second")
    
    # Stream processing benchmarks
    stream_parser = subparsers.add_parser("stream", help="Run stream processing benchmarks")
    stream_parser.add_argument("--duration", type=int, default=30, help="Test duration in seconds")
    stream_parser.add_argument("--users", type=int, default=5, help="Concurrent users")
    stream_parser.add_argument("--rate", type=int, default=50, help="Operations per second")
    
    # Full benchmark suite
    full_parser = subparsers.add_parser("full", help="Run full benchmark suite")
    
    # Production readiness check
    readiness_parser = subparsers.add_parser("readiness", help="Run production readiness validation")
    
    # Resource monitoring
    monitor_parser = subparsers.add_parser("monitor", help="Run resource monitoring")
    monitor_parser.add_argument("--duration", type=int, default=60, help="Monitoring duration in seconds")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Load settings
    if args.env_file:
        global settings
        settings = load_settings(args.env_file)
        print(f"Loaded configuration from: {args.env_file}")
    
    print(f"Environment: {settings.environment.value}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Run the specified command
    try:
        if args.command == "kafka":
            success = run_kafka_benchmarks(args)
        elif args.command == "stream":
            success = run_stream_benchmarks(args)
        elif args.command == "full":
            success = run_full_benchmark_suite(args)
        elif args.command == "readiness":
            success = run_production_readiness_check(args)
        elif args.command == "monitor":
            success = run_resource_monitoring(args)
        else:
            print(f"Unknown command: {args.command}")
            return 1
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user.")
        return 1
    except Exception as e:
        print(f"\nBenchmark failed with error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)