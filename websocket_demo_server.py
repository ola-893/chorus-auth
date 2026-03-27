#!/usr/bin/env python3
"""
WebSocket Demo Server for Chorus Frontend
Creates a real WebSocket server that the frontend can connect to
"""

import asyncio
import json
import random
import websockets
from datetime import datetime
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import threading

class WebSocketDemoServer:
    def __init__(self):
        self.agents = {}
        self.running = False
        self.connected_clients = set()
        self.start_time = time.time()
        
        # Create FastAPI app
        self.app = FastAPI(title="Chorus WebSocket Demo Server")
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3003", "http://localhost:3000", "http://127.0.0.1:3003"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self.setup_routes()
    
    def setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}
        
        @self.app.get("/status")
        async def get_status():
            return {
                "state": "RUNNING",
                "uptime": int(time.time() - self.start_time),
                "is_healthy": True,
                "health": {
                    "overall_status": "healthy",
                    "component_statuses": {
                        "redis": "healthy",
                        "gemini_api": "healthy",
                        "system_resources": "healthy"
                    }
                }
            }
        
        @self.app.get("/agents")
        async def get_agents():
            agents_list = []
            for agent_id, agent_data in self.agents.items():
                agents_list.append({
                    "id": agent_id,
                    "trust_score": agent_data["trustScore"],
                    "status": agent_data["status"],
                    "last_updated": agent_data["lastUpdate"]
                })
            return {"agents": agents_list}
        
        @self.app.get("/dashboard/metrics")
        async def get_dashboard_metrics():
            total_agents = len(self.agents)
            quarantined_count = sum(1 for agent in self.agents.values() if agent["status"] == "quarantined")
            active_agents = total_agents - quarantined_count
            
            return {
                "total_agents": total_agents,
                "active_agents": active_agents,
                "quarantined_agents": quarantined_count,
                "system_health": {
                    "redis": {"healthy": True, "status": "connected"},
                    "gemini_api": {"healthy": True, "status": "connected"},
                    "system_resources": {"healthy": True, "status": "normal"}
                },
                "recent_events": []
            }
        
        @self.app.websocket("/ws/dashboard")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.connected_clients.add(websocket)
            print(f"✅ WebSocket client connected. Total clients: {len(self.connected_clients)}")
            
            try:
                # Send initial system status
                await self.send_system_status(websocket)
                
                # Keep connection alive
                while True:
                    try:
                        # Wait for messages with timeout to send periodic updates
                        message = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
                        data = json.loads(message)
                        print(f"📨 Received: {data}")
                    except asyncio.TimeoutError:
                        # Send periodic system status
                        await self.send_system_status(websocket)
                    except json.JSONDecodeError:
                        print("⚠️ Invalid JSON received")
                        
            except WebSocketDisconnect:
                self.connected_clients.remove(websocket)
                print(f"❌ WebSocket client disconnected. Total clients: {len(self.connected_clients)}")
            except Exception as e:
                print(f"❌ WebSocket error: {e}")
                if websocket in self.connected_clients:
                    self.connected_clients.remove(websocket)
    
    async def create_initial_agents(self, num_agents=6):
        """Create initial agents"""
        print(f"🤖 Creating {num_agents} agents...")
        
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
            
            print(f"  ✅ {agent_id} (trust: {trust_score})")
    
    async def send_system_status(self, websocket):
        """Send system status to a specific client"""
        try:
            uptime = int(time.time() - self.start_time)
            
            # System status
            status_message = {
                "type": "system_status",
                "data": {
                    "state": "RUNNING",
                    "uptime": uptime,
                    "is_healthy": True,
                    "timestamp": datetime.now().isoformat()
                }
            }
            await websocket.send_text(json.dumps(status_message))
            
            # System metrics
            metrics_message = {
                "type": "system_metrics",
                "data": {
                    "metrics": {
                        "memory_usage": random.uniform(60, 85),
                        "cpu_usage": random.uniform(20, 40),
                        "active_connections": len(self.connected_clients),
                        "requests_per_minute": random.randint(120, 180),
                        "error_rate": random.uniform(0.1, 0.8)
                    }
                }
            }
            await websocket.send_text(json.dumps(metrics_message))
            
        except Exception as e:
            print(f"❌ Error sending system status: {e}")
    
    async def broadcast_to_all_clients(self, message):
        """Broadcast message to all connected WebSocket clients"""
        if not self.connected_clients:
            return
        
        message_str = json.dumps(message)
        disconnected = []
        
        for websocket in self.connected_clients.copy():
            try:
                await websocket.send_text(message_str)
            except Exception as e:
                print(f"⚠️ Failed to send to client: {e}")
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for websocket in disconnected:
            self.connected_clients.discard(websocket)
    
    async def simulate_agent_activity(self):
        """Simulate ongoing agent activity"""
        print("🎬 Starting agent activity simulation...")
        
        while self.running:
            try:
                if not self.agents:
                    await asyncio.sleep(2)
                    continue
                
                # Select random agent
                agent_id = random.choice(list(self.agents.keys()))
                agent = self.agents[agent_id]
                
                # Simulate trust score change
                old_score = agent["trustScore"]
                change = random.randint(-15, 10)
                new_score = max(0, min(100, old_score + change))
                
                # Update agent
                agent["trustScore"] = new_score
                agent["status"] = "quarantined" if new_score < 30 else "active"
                agent["lastUpdate"] = datetime.now().isoformat()
                agent["riskLevel"] = "high" if new_score < 30 else "medium" if new_score < 70 else "low"
                
                # Update resource usage
                agent["resourceUsage"]["cpu"] = max(0, min(100, agent["resourceUsage"]["cpu"] + random.randint(-10, 10)))
                agent["resourceUsage"]["memory"] = max(0, min(100, agent["resourceUsage"]["memory"] + random.randint(-5, 5)))
                agent["resourceUsage"]["network"] = max(0, min(100, agent["resourceUsage"]["network"] + random.randint(-15, 15)))
                
                # Broadcast trust score update
                update_message = {
                    "type": "trust_score_update",
                    "agent_id": agent_id,
                    "old_score": old_score,
                    "new_score": new_score,
                    "change": change,
                    "timestamp": datetime.now().isoformat()
                }
                
                await self.broadcast_to_all_clients(update_message)
                
                # Check for quarantine events
                if new_score < 30 and old_score >= 30:
                    quarantine_message = {
                        "type": "quarantine_event",
                        "agent_id": agent_id,
                        "action": "quarantine",
                        "reason": f"Trust score below threshold: {new_score} < 30",
                        "timestamp": datetime.now().isoformat()
                    }
                    await self.broadcast_to_all_clients(quarantine_message)
                    print(f"🚫 Quarantined {agent_id} (trust: {new_score})")
                
                elif new_score >= 30 and old_score < 30:
                    release_message = {
                        "type": "quarantine_event",
                        "agent_id": agent_id,
                        "action": "release",
                        "reason": f"Trust score recovered: {new_score} >= 30",
                        "timestamp": datetime.now().isoformat()
                    }
                    await self.broadcast_to_all_clients(release_message)
                    print(f"✅ Released {agent_id} from quarantine (trust: {new_score})")
                
                # Log the change
                if change != 0:
                    change_icon = "⬆️" if change > 0 else "⬇️"
                    print(f"  {change_icon} {agent_id}: {old_score} → {new_score}")
                
                await asyncio.sleep(random.uniform(1, 3))
                
            except Exception as e:
                print(f"❌ Error in agent simulation: {e}")
                await asyncio.sleep(2)
    
    async def simulate_system_health(self):
        """Simulate system health updates"""
        while self.running:
            try:
                # Circuit breaker updates
                services = ["redis", "datadog", "gemini_api"]
                for service in services:
                    if random.random() < 0.1:  # 10% chance
                        cb_message = {
                            "type": "circuit_breaker_update",
                            "data": {
                                "service_name": service,
                                "state": random.choice(["CLOSED", "CLOSED", "CLOSED", "HALF_OPEN"]),
                                "failure_count": random.randint(0, 2),
                                "last_failure_time": datetime.now().isoformat() if random.random() < 0.3 else None
                            }
                        }
                        await self.broadcast_to_all_clients(cb_message)
                
                # Dependency status
                deps_message = {
                    "type": "dependency_status",
                    "data": {
                        "dependencies": [
                            {
                                "name": "Redis",
                                "status": "connected",
                                "last_check": datetime.now().isoformat(),
                                "response_time": random.uniform(1, 5)
                            },
                            {
                                "name": "Datadog API",
                                "status": "connected",
                                "last_check": datetime.now().isoformat(),
                                "response_time": random.uniform(40, 60)
                            },
                            {
                                "name": "Gemini API",
                                "status": "connected",
                                "last_check": datetime.now().isoformat(),
                                "response_time": random.uniform(100, 150)
                            }
                        ]
                    }
                }
                await self.broadcast_to_all_clients(deps_message)
                
                await asyncio.sleep(8)  # Update every 8 seconds
                
            except Exception as e:
                print(f"❌ Error in system health simulation: {e}")
                await asyncio.sleep(5)
    
    async def run_simulation(self, duration=300):
        """Run the simulation"""
        self.running = True
        
        print(f"🎬 Starting WebSocket Demo Server")
        print(f"⏱️  Duration: {duration} seconds")
        print(f"🌐 Server: http://localhost:8000")
        print(f"📡 WebSocket: ws://localhost:8000/ws/dashboard")
        print("=" * 60)
        
        # Create initial agents
        await self.create_initial_agents(6)
        
        # Start simulation tasks
        agent_task = asyncio.create_task(self.simulate_agent_activity())
        health_task = asyncio.create_task(self.simulate_system_health())
        
        try:
            # Run for specified duration
            await asyncio.sleep(duration)
        except KeyboardInterrupt:
            print("\n🛑 Demo interrupted")
        finally:
            self.running = False
            agent_task.cancel()
            health_task.cancel()
            
            # Wait for tasks to complete
            try:
                await agent_task
            except asyncio.CancelledError:
                pass
            try:
                await health_task
            except asyncio.CancelledError:
                pass
    
    def start_server(self):
        """Start the FastAPI server"""
        config = uvicorn.Config(
            app=self.app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
        server = uvicorn.Server(config)
        return server

async def main():
    demo_server = WebSocketDemoServer()
    
    # Start server and simulation concurrently
    server = demo_server.start_server()
    
    server_task = asyncio.create_task(server.serve())
    simulation_task = asyncio.create_task(demo_server.run_simulation(300))  # 5 minutes
    
    print("🚀 WebSocket Demo Server Starting...")
    print("📊 Open http://localhost:3003 to see the frontend")
    print("🔌 Frontend will connect to ws://localhost:8000/ws/dashboard")
    print("🛑 Press Ctrl+C to stop")
    
    try:
        # Wait for either task to complete
        done, pending = await asyncio.wait(
            [server_task, simulation_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel remaining tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
                
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")