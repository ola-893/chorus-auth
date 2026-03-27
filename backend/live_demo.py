#!/usr/bin/env python3
"""
Live Demo Script for Chorus Multi-Agent Immune System

This script simulates real agent activity to demonstrate the dashboard
receiving live updates via WebSocket.
"""

import asyncio
import json
import time
import sys
import os
import random
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.event_bus import event_bus
from src.prediction_engine.trust_manager import trust_manager as global_trust_manager
from src.prediction_engine.quarantine_manager import quarantine_manager, RedisQuarantineManager
from src.mapper.topology_manager import topology_manager
from src.prediction_engine.pattern_detector import PatternDetector

class LiveDemoRunner:
    def __init__(self):
        self.trust_manager = global_trust_manager  # Use global instance
        self.quarantine_manager = quarantine_manager  # Use global instance
        self.pattern_detector = PatternDetector()
        self.agents = []
        
    def log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def create_agents(self, count: int = 5):
        """Create simulated agents"""
        self.agents = [f"agent_{i:03d}" for i in range(count)]
        self.log(f"Created {count} agents: {', '.join(self.agents)}")
        
        # Initialize trust scores
        for agent_id in self.agents:
            initial_score = random.randint(60, 100)
            self.trust_manager.update_trust_score(
                agent_id=agent_id,
                adjustment=initial_score - 50,  # Adjust from default 50
                reason="Initial agent registration"
            )
            self.log(f"  {agent_id}: Initial trust score {initial_score}")
            
    def simulate_agent_interaction(self, source: str, target: str):
        """Simulate an interaction between two agents"""
        interaction_types = ["request", "response", "broadcast", "query"]
        interaction_type = random.choice(interaction_types)
        
        # Add edge to causal graph
        topology_manager.add_interaction(source, target, interaction_type)
        
        self.log(f"  {source} -> {target} ({interaction_type})")
        
    def simulate_trust_change(self, agent_id: str, delta: int, reason: str):
        """Simulate a trust score change"""
        self.trust_manager.update_trust_score(
            agent_id=agent_id,
            adjustment=delta,
            reason=reason
        )
        
        new_score = self.trust_manager.get_trust_score(agent_id)
        self.log(f"  {agent_id}: Trust {'+' if delta > 0 else ''}{delta} -> {new_score} ({reason})")
        
    def simulate_pattern_detection(self, pattern_type: str, agents: list):
        """Simulate pattern detection"""
        severity = "critical" if pattern_type in ["routing_loop", "byzantine_behavior"] else "warning"
        
        pattern_alert = {
            "type": "pattern_alert",
            "data": {
                "agent_id": agents[0],
                "patterns": [pattern_type.upper()],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "severity": severity,
                "type": pattern_type,
                "details": f"Detected {pattern_type.replace('_', ' ')} involving {len(agents)} agents",
                "recommended_action": f"Review {pattern_type.replace('_', ' ')} and consider intervention",
                "affected_agents": agents,
                "risk_score": random.uniform(0.6, 0.95)
            }
        }
        
        event_bus.publish("pattern_alert", pattern_alert)
        self.log(f"  ⚠️ Pattern detected: {pattern_type} affecting {', '.join(agents)}")
        
    def simulate_quarantine(self, agent_id: str, reason: str):
        """Simulate quarantining an agent"""
        result = self.quarantine_manager.quarantine_agent(agent_id, reason)
        if result.success:
            self.log(f"  🔒 {agent_id} QUARANTINED: {reason}")
        else:
            self.log(f"  ❌ Failed to quarantine {agent_id}: {result.reason}")
            
    async def run_scenario_normal_operations(self):
        """Scenario 1: Normal agent operations"""
        self.log("\n" + "="*60)
        self.log("SCENARIO 1: Normal Agent Operations")
        self.log("="*60)
        
        # Create agents
        self.create_agents(5)
        await asyncio.sleep(1)
        
        # Simulate normal interactions
        self.log("\nSimulating normal agent interactions...")
        for _ in range(10):
            source = random.choice(self.agents)
            target = random.choice([a for a in self.agents if a != source])
            self.simulate_agent_interaction(source, target)
            await asyncio.sleep(0.5)
            
        # Simulate positive trust changes
        self.log("\nSimulating cooperation bonuses...")
        for agent_id in random.sample(self.agents, 3):
            self.simulate_trust_change(agent_id, random.randint(5, 15), "Successful cooperation")
            await asyncio.sleep(0.3)
            
    async def run_scenario_conflict_detection(self):
        """Scenario 2: Conflict detection and intervention"""
        self.log("\n" + "="*60)
        self.log("SCENARIO 2: Conflict Detection & Intervention")
        self.log("="*60)
        
        # Simulate suspicious behavior
        self.log("\nSimulating suspicious agent behavior...")
        bad_agent = random.choice(self.agents)
        
        for _ in range(5):
            self.simulate_trust_change(bad_agent, random.randint(-10, -5), "Resource hoarding detected")
            await asyncio.sleep(0.5)
            
        # Detect pattern
        self.log("\nPattern detection triggered...")
        self.simulate_pattern_detection("resource_hoarding", [bad_agent])
        await asyncio.sleep(1)
        
        # Check if quarantine needed
        score = self.trust_manager.get_trust_score(bad_agent)
        if score < 30:
            self.simulate_quarantine(bad_agent, "Trust score below threshold")
            
    async def run_scenario_routing_loop(self):
        """Scenario 3: Routing loop detection"""
        self.log("\n" + "="*60)
        self.log("SCENARIO 3: Routing Loop Detection")
        self.log("="*60)
        
        # Create a routing loop
        loop_agents = self.agents[:3]
        self.log(f"\nCreating routing loop: {' -> '.join(loop_agents)} -> {loop_agents[0]}")
        
        for i in range(len(loop_agents)):
            source = loop_agents[i]
            target = loop_agents[(i + 1) % len(loop_agents)]
            self.simulate_agent_interaction(source, target)
            await asyncio.sleep(0.3)
            
        # Detect the loop
        self.log("\nRouting loop detected!")
        self.simulate_pattern_detection("routing_loop", loop_agents)
        await asyncio.sleep(1)
        
        # Penalize involved agents
        for agent_id in loop_agents:
            self.simulate_trust_change(agent_id, -15, "Involved in routing loop")
            await asyncio.sleep(0.3)
            
    async def run_scenario_byzantine_behavior(self):
        """Scenario 4: Byzantine behavior detection"""
        self.log("\n" + "="*60)
        self.log("SCENARIO 4: Byzantine Behavior Detection")
        self.log("="*60)
        
        # Simulate inconsistent communication
        byzantine_agent = random.choice(self.agents)
        self.log(f"\nAgent {byzantine_agent} exhibiting inconsistent behavior...")
        
        # Multiple conflicting messages
        for target in random.sample([a for a in self.agents if a != byzantine_agent], 3):
            self.simulate_agent_interaction(byzantine_agent, target)
            self.simulate_trust_change(byzantine_agent, -8, "Inconsistent message detected")
            await asyncio.sleep(0.4)
            
        # Detect byzantine behavior
        self.simulate_pattern_detection("byzantine_behavior", [byzantine_agent])
        await asyncio.sleep(1)
        
        # Quarantine if needed
        score = self.trust_manager.get_trust_score(byzantine_agent)
        if score < 30:
            self.simulate_quarantine(byzantine_agent, "Byzantine behavior confirmed")
            
    async def run_full_demo(self):
        """Run the complete demo"""
        self.log("\n" + "="*60)
        self.log("CHORUS LIVE DEMO - Multi-Agent Immune System")
        self.log("="*60)
        self.log("Open http://localhost:3000/dashboard to see live updates")
        self.log("="*60)
        
        await asyncio.sleep(2)
        
        # Run all scenarios
        await self.run_scenario_normal_operations()
        await asyncio.sleep(2)
        
        await self.run_scenario_conflict_detection()
        await asyncio.sleep(2)
        
        await self.run_scenario_routing_loop()
        await asyncio.sleep(2)
        
        await self.run_scenario_byzantine_behavior()
        
        self.log("\n" + "="*60)
        self.log("DEMO COMPLETE")
        self.log("="*60)
        
        # Final status
        self.log("\nFinal Agent Status:")
        for agent_id in self.agents:
            score = self.trust_manager.get_trust_score(agent_id)
            is_quarantined = self.quarantine_manager.is_quarantined(agent_id)
            status = "🔒 QUARANTINED" if is_quarantined else "✅ ACTIVE"
            self.log(f"  {agent_id}: Trust={score}, Status={status}")


async def main():
    runner = LiveDemoRunner()
    await runner.run_full_demo()


if __name__ == "__main__":
    asyncio.run(main())
