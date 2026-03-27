#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demonstration script for the agent simulation environment.
"""
import time
import logging
from src.prediction_engine.simulator import AgentNetwork

# Configure logging to see agent activity
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Run a demonstration of the agent simulation."""
    print("🤖 Starting Agent Conflict Predictor Simulation Demo")
    print("=" * 60)
    
    # Create agent network
    network = AgentNetwork(min_agents=5, max_agents=7)
    
    try:
        # Start simulation
        print("🚀 Starting simulation with autonomous agents...")
        network.start_simulation()
        
        print(f"✅ Created {len(network.agents)} agents:")
        for agent in network.agents:
            print(f"   - {agent.agent_id} (trust score: {agent.trust_score})")
        
        # Let simulation run
        print("\n⏱️  Running simulation for 10 seconds...")
        for i in range(10):
            time.sleep(1)
            
            # Show status every 2 seconds
            if i % 2 == 0:
                active_agents = network.get_active_agents()
                quarantined = [a for a in network.agents if a.is_quarantined]
                intentions = network.get_all_intentions()
                contention = network.resource_manager.detect_contention()
                
                print(f"   Status: {len(active_agents)} active, "
                      f"{len(quarantined)} quarantined, "
                      f"{len(intentions)} intentions, "
                      f"{len(contention)} contentions")
        
        # Demonstrate quarantine
        print("\n🚨 Demonstrating quarantine functionality...")
        first_agent = network.agents[0]
        print(f"   Quarantining {first_agent.agent_id}")
        network.quarantine_agent(first_agent.agent_id)
        
        time.sleep(2)
        
        print(f"   Releasing {first_agent.agent_id} from quarantine")
        network.release_agent_quarantine(first_agent.agent_id)
        
        # Show final status
        print("\n📊 Final simulation status:")
        for agent in network.agents:
            intentions_count = len(agent.get_current_intentions())
            status = "quarantined" if agent.is_quarantined else "active"
            print(f"   - {agent.agent_id}: {status}, {intentions_count} intentions")
        
        # Show resource usage
        print("\n💾 Resource usage:")
        from src.prediction_engine.models.core import ResourceType
        for resource_type in ResourceType:
            status = network.resource_manager.get_resource_status(resource_type.value)
            utilization = status.current_usage / max(status.total_capacity, 1) * 100
            print(f"   - {resource_type.value}: {utilization:.1f}% "
                  f"({status.current_usage}/{status.total_capacity})")
        
    except KeyboardInterrupt:
        print("\n⏹️  Simulation interrupted by user")
    
    finally:
        # Stop simulation
        print("\n🛑 Stopping simulation...")
        network.stop_simulation()
        print("✅ Simulation stopped successfully")
    
    print("\n🎉 Demo completed!")


if __name__ == "__main__":
    main()