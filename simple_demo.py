#!/usr/bin/env python3
"""
Simple Demo Script for Chorus Frontend
Generates mock data and sends it via WebSocket to demonstrate the frontend
"""

import asyncio
import json
import random
import websockets
from datetime import datetime
import time

class SimpleFrontendDemo:
    def __init__(self):
        self.agents = {}
        self.running = False
        
    async def create_mock_agents(self, num_agents=6):
        """Create mock agents with initial data"""
        print(f"🤖 Creating {num_agents} mock agents...")
        
        for i in range(num_agents):
            agent_id = f"demo_agent_{i+1:03d}"
            trust_score = random.randint(60, 100)
            
            self.agents[agent_id] = {
                "id": agent_id,
                "trustScore": trust_score,
                "status": "quarantined" if trust_score < 30 else "active",
                "lastUpdate": datetime.now().isoformat(),
                "riskLevel": "high" if trust_score < 30 else "medium" if trust_score < 70 else "low",
                "activityLevel": random.randint(20, 100),
                "resourceUsage": {
                    "cpu": random.randint(10, 90),
                    "memory": random.randint(20, 85),
                    "network": random.randint(5, 60)
                }
            }
            
            print(f"  ✅ Created {agent_id} (trust: {trust_score})")
    
    async def simulate_agent_updates(self, websocket):
        """Simulate real-time agent updates"""
        print("🎬 Starting agent simulation...")
        
        while self.running:
            try:
                # Select random agent for update
                if not self.agents:
                    await asyncio.sleep(2)
                    continue
                
                agent_id = random.choice(list(self.agents.keys()))
                agent = self.agents[agent_id]
                
                # Simulate trust score change
                old_score = agent["trustScore"]
                change = random.randint(-15, 10)
                new_score = max(0, min(100, old_score + change))
                
                # Update agent data
                agent["trustScore"] = new_score
                agent["status"] = "quarantined" if new_score < 30 else "active"
                agent["lastUpdate"] = datetime.now().isoformat()
                agent["riskLevel"] = "high" if new_score < 30 else "medium" if new_score < 70 else "low"
                
                # Update resource usage
                agent["resourceUsage"]["cpu"] = max(0, min(100, agent["resourceUsage"]["cpu"] + random.randint(-10, 10)))
                agent["resourceUsage"]["memory"] = max(0, min(100, agent["resourceUsage"]["memory"] + random.randint(-5, 5)))
                agent["resourceUsage"]["network"] = max(0, min(100, agent["resourceUsage"]["network"] + random.randint(-15, 15)))
                
                # Send trust score update
                update_message = {
                    "type": "trust_score_update",
                    "agent_id": agent_id,
                    "old_score": old_score,
                    "new_score": new_score,
                    "change": change,
                    "timestamp": datetime.now().isoformat()
                }
                
                await websocket.send(json.dumps(update_message))
                
                # Check for quarantine events
                if new_score < 30 and old_score >= 30:
                    quarantine_message = {
                        "type": "quarantine_event",
                        "agent_id": agent_id,
                        "action": "quarantine",
                        "reason": f"Trust score below threshold: {new_score} < 30",
                        "timestamp": datetime.now().isoformat()
                    }
                    await websocket.send(json.dumps(quarantine_message))
                    print(f"🚫 Quarantined {agent_id} (trust: {new_score})")
                
                elif new_score >= 30 and old_score < 30:
                    release_message = {
                        "type": "quarantine_event",
                        "agent_id": agent_id,
                        "action": "release",
                        "reason": f"Trust score recovered: {new_score} >= 30",
                        "timestamp": datetime.now().isoformat()
                    }
                    await websocket.send(json.dumps(release_message))
                    print(f"✅ Released {agent_id} from quarantine (trust: {new_score})")
                
                # Log the change
                if change != 0:
                    change_icon = "⬆️" if change > 0 else "⬇️"
                    print(f"  {change_icon} {agent_id}: {old_score} → {new_score}")
                
                await asyncio.sleep(random.uniform(1, 3))
                
            except Exception as e:
                print(f"❌ Error in agent simulation: {e}")
                await asyncio.sleep(2)
    
    async def simulate_system_health(self, websocket):
        """Simulate system health updates"""
        while self.running:
            try:
                # System status
                status_message = {
                    "type": "system_status",
                    "data": {
                        "state": "RUNNING",
                        "uptime": int(time.time() - self.start_time),
                        "is_healthy": True,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                await websocket.send(json.dumps(status_message))
                
                # System metrics
                metrics_message = {
                    "type": "system_metrics",
                    "data": {
                        "metrics": {
                            "memory_usage": random.uniform(60, 85),
                            "cpu_usage": random.uniform(20, 40),
                            "active_connections": random.randint(8, 15),
                            "requests_per_minute": random.randint(120, 180),
                            "error_rate": random.uniform(0.1, 0.8)
                        }
                    }
                }
                await websocket.send(json.dumps(metrics_message))
                
                # Circuit breaker updates
                services = ["redis", "datadog", "gemini_api"]
                for service in services:
                    if random.random() < 0.1:  # 10% chance of update
                        cb_message = {
                            "type": "circuit_breaker_update",
                            "data": {
                                "service_name": service,
                                "state": random.choice(["CLOSED", "CLOSED", "CLOSED", "HALF_OPEN"]),  # Mostly closed
                                "failure_count": random.randint(0, 2),
                                "last_failure_time": datetime.now().isoformat() if random.random() < 0.3 else None
                            }
                        }
                        await websocket.send(json.dumps(cb_message))
                
                await asyncio.sleep(5)  # Update every 5 seconds
                
            except Exception as e:
                print(f"❌ Error in system health simulation: {e}")
                await asyncio.sleep(5)
    
    async def run_demo(self, duration=180):
        """Run the demo for specified duration"""
        self.start_time = time.time()
        self.running = True
        
        print(f"🎬 Starting Simple Frontend Demo")
        print(f"⏱️  Duration: {duration} seconds")
        print(f"🌐 Frontend: http://localhost:3003")
        print("=" * 60)
        
        # Create mock agents
        await self.create_mock_agents(6)
        
        print(f"\n📡 Connecting to frontend WebSocket...")
        
        try:
            # Connect to the frontend's WebSocket (if it has one)
            # For now, we'll just simulate the data generation
            
            # Create a mock websocket-like object for demonstration
            class MockWebSocket:
                async def send(self, data):
                    # Parse and display the data being "sent"
                    try:
                        message = json.loads(data)
                        if message["type"] == "trust_score_update":
                            pass  # Already logged above
                        elif message["type"] == "system_status":
                            pass  # Don't spam logs
                        elif message["type"] == "quarantine_event":
                            pass  # Already logged above
                    except:
                        pass
            
            websocket = MockWebSocket()
            
            # Start simulation tasks
            agent_task = asyncio.create_task(self.simulate_agent_updates(websocket))
            health_task = asyncio.create_task(self.simulate_system_health(websocket))
            
            print(f"✅ Demo simulation started!")
            print(f"📊 Watch the frontend at http://localhost:3003 for real-time updates")
            print(f"🤖 {len(self.agents)} agents are being simulated")
            print(f"\n🎯 Demo Features:")
            print(f"   • Real-time trust score changes")
            print(f"   • Automatic quarantine/release events")
            print(f"   • System health monitoring")
            print(f"   • Resource usage simulation")
            print(f"\n🛑 Press Ctrl+C to stop")
            
            # Run for specified duration
            await asyncio.sleep(duration)
            
        except KeyboardInterrupt:
            print(f"\n🛑 Demo interrupted by user")
        finally:
            self.running = False
            print(f"\n🧹 Demo completed!")
            
            # Cancel tasks
            if 'agent_task' in locals():
                agent_task.cancel()
            if 'health_task' in locals():
                health_task.cancel()

async def main():
    demo = SimpleFrontendDemo()
    await demo.run_demo(180)  # Run for 3 minutes

if __name__ == "__main__":
    print("🚀 Chorus Simple Frontend Demo")
    print("This demo simulates agent activity for the frontend dashboard")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo stopped by user")