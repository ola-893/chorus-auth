#!/usr/bin/env python3
"""
Performance and load testing for the Agent Conflict Predictor system.

Tests system performance under expected load (10 agents) and validates
concurrent operations and resource contention scenarios.
"""

import time
import threading
from datetime import datetime
from typing import List, Dict, Any

from src.prediction_engine.system_integration import ConflictPredictorSystem
from src.prediction_engine.simulator import AgentNetwork
from src.prediction_engine.models.core import AgentIntention


def test_system_performance_10_agents():
    """Test system performance with 10 agents (expected load)."""
    print("Testing system performance with 10 agents...")
    
    system = ConflictPredictorSystem()
    start_time = time.time()
    
    try:
        # Start system with 10 agents
        system.start_system(agent_count=10)
        
        startup_time = time.time() - start_time
        print(f"System startup time: {startup_time:.2f} seconds")
        
        # Verify system started correctly
        status = system.get_system_status()
        assert status["system_running"] is True
        assert status["total_agents"] == 10
        print(f"✓ System started with {status['total_agents']} agents")
        
        # Let system run for a period to generate activity
        print("Running system for 30 seconds to generate activity...")
        time.sleep(30)
        
        # Check system stability
        final_status = system.get_system_status()
        print(f"Final status: {final_status['active_agents']} active, {final_status['quarantined_agents']} quarantined")
        
        # Verify system maintained stability
        assert final_status["system_running"] is True
        assert final_status["total_agents"] == 10
        
        total_time = time.time() - start_time
        print(f"✓ System maintained stability for {total_time:.2f} seconds")
        
        return True
        
    except Exception as e:
        print(f"✗ Performance test failed: {e}")
        return False
    finally:
        system.stop_system()


def test_concurrent_operations():
    """Test concurrent operations and resource contention scenarios."""
    print("\nTesting concurrent operations...")
    
    network = AgentNetwork(min_agents=8, max_agents=8)
    
    try:
        agents = network.create_agents(8)
        network.start_simulation()
        
        # Create concurrent resource requests
        def create_concurrent_requests():
            """Create multiple concurrent resource requests."""
            intentions = []
            for i, agent in enumerate(agents):
                intention = AgentIntention(
                    agent_id=agent.agent_id,
                    resource_type="cpu",
                    requested_amount=200,  # High resource usage
                    priority_level=5 + (i % 3),  # Varying priorities
                    timestamp=datetime.now()
                )
                agent._current_intentions = [intention]
                intentions.append(intention)
            return intentions
        
        # Run concurrent operations
        threads = []
        for _ in range(5):  # 5 concurrent threads
            thread = threading.Thread(target=create_concurrent_requests)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Let system process the concurrent requests
        time.sleep(5)
        
        # Verify system handled concurrent operations
        active_agents = network.get_active_agents()
        print(f"✓ System handled concurrent operations: {len(active_agents)} agents still active")
        
        return True
        
    except Exception as e:
        print(f"✗ Concurrent operations test failed: {e}")
        return False
    finally:
        network.stop_simulation()


def test_high_throughput_operations():
    """Test system maintains stability during high-throughput operations."""
    print("\nTesting high-throughput operations...")
    
    network = AgentNetwork(min_agents=6, max_agents=6)
    
    try:
        agents = network.create_agents(6)
        network.start_simulation()
        
        # Generate high-throughput operations
        start_time = time.time()
        operation_count = 0
        
        while time.time() - start_time < 10:  # Run for 10 seconds
            for agent in agents:
                # Rapidly change agent intentions
                intention = AgentIntention(
                    agent_id=agent.agent_id,
                    resource_type=["cpu", "memory", "storage"][operation_count % 3],
                    requested_amount=50 + (operation_count % 100),
                    priority_level=1 + (operation_count % 10),
                    timestamp=datetime.now()
                )
                agent._current_intentions = [intention]
                operation_count += 1
            
            time.sleep(0.1)  # Brief pause between batches
        
        throughput = operation_count / 10
        print(f"✓ Achieved throughput: {throughput:.1f} operations/second")
        
        # Verify system stability
        active_agents = network.get_active_agents()
        assert len(active_agents) > 0, "System should maintain active agents"
        
        return True
        
    except Exception as e:
        print(f"✗ High-throughput test failed: {e}")
        return False
    finally:
        network.stop_simulation()


def main():
    """Run all performance tests."""
    print("=== Agent Conflict Predictor Performance Tests ===\n")
    
    tests = [
        test_system_performance_10_agents,
        test_concurrent_operations,
        test_high_throughput_operations
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}\n")
    
    print(f"=== Performance Test Results ===")
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("✓ All performance tests passed!")
        return True
    else:
        print("✗ Some performance tests failed.")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)