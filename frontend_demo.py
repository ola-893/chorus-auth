#!/usr/bin/env python3
"""
Frontend Demo for Chorus Multi-Agent Immune System

This script creates a comprehensive demo that includes:
1. Backend API server with WebSocket support
2. Real-time data generation for frontend visualization
3. Simulated agent activities and trust score changes
4. Live conflict prediction and intervention events

Usage:
    python frontend_demo.py [--duration SECONDS] [--agents COUNT]
"""

import asyncio
import argparse
import sys
import os
import json
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from pathlib import Path

# Add backend src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src'))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
from pydantic import BaseModel

# Import our system components
from prediction_engine.simulator import AgentSimulator
from prediction_engine.trust_manager import TrustManager
from prediction_engine.intervention_engine import InterventionEngine
from prediction_engine.gemini_client import GeminiClient
from prediction_engine.redis_client import RedisClient
from prediction_engine.system_integration import SystemIntegration
from config import Config
from logging_config import setup_logging

class FrontendDemo:
    """Comprehensive frontend demo with real-time updates."""
    
    def __init__(self, duration: int = 600, num_agents: int = 8):
        self.duration = duration
        self.num_agents = num_agents
        self.config = Config()
        self.logger = setup_logging()
        
        # System components
        self.redis_client = None
        self.gemini_client = None
        self.trust_manager = None
        self.intervention_engine = None
        self.simulator = None
        self.system_integration = None
        
        # Demo state
        self.agents = {}
        self.active_connections = []
        self.demo_start_time = None
        self.running = False
        
        # Create FastAPI app
        self.app = self.create_app()
    
    def create_app(self) -> FastAPI:
        """Create the FastAPI application with all endpoints."""
        app = FastAPI(
            title="Chorus Agent Conflict Predictor API",
            description="Real-time multi-agent immune system",
            version="1.0.0"
        )
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # API Models
        class SystemStatus(BaseModel):
            state: str
            uptime: float
            is_healthy: bool
            health: Optional[dict] = None
        
        class AgentTrustScore(BaseModel):
            agent_id: str
            trust_score: float
            status: str
            last_updated: str
        
        class DashboardMetrics(BaseModel):
            total_agents: int
            active_agents: int
            quarantined_agents: int
            system_health: dict
            recent_events: List[dict]
        
        # Authentication helper
        def verify_api_key(x_agent_api_key: str = Header(None)):
            if x_agent_api_key != "demo-key":
                raise HTTPException(status_code=401, detail="Invalid API key")
            return x_agent_api_key
        
        # API Endpoints
        @app.get("/health")
        async def health_check():
            """System health check endpoint."""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0"
            }
        
        @app.get("/status", response_model=SystemStatus)
        async def get_system_status(api_key: str = Header(None, alias="X-Agent-API-Key")):
            """Get comprehensive system status."""
            verify_api_key(api_key)
            
            if not self.system_integration:
                raise HTTPException(status_code=503, detail="System not initialized")
            
            uptime = (datetime.now() - self.demo_start_time).total_seconds() if self.demo_start_time else 0
            health_status = await self.system_integration.get_system_health()
            
            return SystemStatus(
                state="running" if self.running else "stopped",
                uptime=uptime,
                is_healthy=all(status.get("healthy", False) for status in health_status.values()),
                health={
                    "overall_status": "healthy",
                    "component_statuses": {name: status.get("status", "unknown") for name, status in health_status.items()}
                }
            )
        
        @app.get("/agents")
        async def get_all_agents(api_key: str = Header(None, alias="X-Agent-API-Key")):
            """Get all agents and their current status."""
            verify_api_key(api_key)
            
            agents_data = []
            for agent_id, agent_data in self.agents.items():
                trust_score = await self.trust_manager.get_trust_score(agent_id) if self.trust_manager else 100
                agents_data.append({
                    "id": agent_id,
                    "trust_score": trust_score,
                    "status": "quarantined" if trust_score < self.config.trust_score_threshold else "active",
                    "last_updated": agent_data.get("last_updated", datetime.now().isoformat())
                })
            
            return {"agents": agents_data}
        
        @app.get("/agents/{agent_id}/trust-score", response_model=AgentTrustScore)
        async def get_agent_trust_score(agent_id: str, api_key: str = Header(None, alias="X-Agent-API-Key")):
            """Get specific agent's trust score."""
            verify_api_key(api_key)
            
            if agent_id not in self.agents:
                raise HTTPException(status_code=404, detail="Agent not found")
            
            trust_score = await self.trust_manager.get_trust_score(agent_id) if self.trust_manager else 100
            
            return AgentTrustScore(
                agent_id=agent_id,
                trust_score=trust_score,
                status="quarantined" if trust_score < self.config.trust_score_threshold else "active",
                last_updated=self.agents[agent_id].get("last_updated", datetime.now().isoformat())
            )
        
        @app.get("/dashboard/metrics", response_model=DashboardMetrics)
        async def get_dashboard_metrics(api_key: str = Header(None, alias="X-Agent-API-Key")):
            """Get metrics for the dashboard."""
            verify_api_key(api_key)
            
            total_agents = len(self.agents)
            quarantined_count = 0
            
            if self.trust_manager:
                for agent_id in self.agents.keys():
                    trust_score = await self.trust_manager.get_trust_score(agent_id)
                    if trust_score < self.config.trust_score_threshold:
                        quarantined_count += 1
            
            active_agents = total_agents - quarantined_count
            
            health_status = await self.system_integration.get_system_health() if self.system_integration else {}
            
            return DashboardMetrics(
                total_agents=total_agents,
                active_agents=active_agents,
                quarantined_agents=quarantined_count,
                system_health=health_status,
                recent_events=[]  # TODO: Implement event history
            )
        
        @app.websocket("/ws/dashboard")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time dashboard updates."""
            await websocket.accept()
            self.active_connections.append(websocket)
            
            try:
                # Send initial system status
                await self.send_system_status(websocket)
                
                # Keep connection alive and handle messages
                while True:
                    try:
                        # Wait for messages (with timeout to send periodic updates)
                        message = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
                        # Handle incoming messages if needed
                        data = json.loads(message)
                        self.logger.info(f"Received WebSocket message: {data}")
                    except asyncio.TimeoutError:
                        # Send periodic updates
                        await self.send_system_status(websocket)
                    except json.JSONDecodeError:
                        self.logger.warning("Invalid JSON received from WebSocket")
                        
            except WebSocketDisconnect:
                self.active_connections.remove(websocket)
                self.logger.info("WebSocket client disconnected")
            except Exception as e:
                self.logger.error(f"WebSocket error: {e}")
                if websocket in self.active_connections:
                    self.active_connections.remove(websocket)
        
        return app
    
    async def initialize_system(self):
        """Initialize all system components."""
        print("🚀 Initializing Chorus system for frontend demo...")
        
        try:
            # Initialize Redis client
            self.redis_client = RedisClient()
            await self.redis_client.connect()
            print("✅ Redis client connected")
            
            # Initialize Gemini client
            self.gemini_client = GeminiClient()
            print("✅ Gemini client initialized")
            
            # Initialize trust manager
            self.trust_manager = TrustManager(self.redis_client)
            print("✅ Trust manager initialized")
            
            # Initialize intervention engine
            self.intervention_engine = InterventionEngine(
                trust_manager=self.trust_manager,
                redis_client=self.redis_client
            )
            print("✅ Intervention engine initialized")
            
            # Initialize agent simulator
            self.simulator = AgentSimulator(
                trust_manager=self.trust_manager,
                intervention_engine=self.intervention_engine,
                gemini_client=self.gemini_client
            )
            print("✅ Agent simulator initialized")
            
            # Initialize system integration
            self.system_integration = SystemIntegration(
                simulator=self.simulator,
                trust_manager=self.trust_manager,
                intervention_engine=self.intervention_engine,
                gemini_client=self.gemini_client,
                redis_client=self.redis_client
            )
            print("✅ System integration initialized")
            
            # Create initial agents
            await self.create_initial_agents()
            
            print("🎯 System initialization complete!")
            
        except Exception as e:
            print(f"❌ System initialization failed: {e}")
            raise
    
    async def create_initial_agents(self):
        """Create initial set of agents for the demo."""
        print(f"🤖 Creating {self.num_agents} initial agents...")
        
        for i in range(self.num_agents):
            agent_id = f"demo_agent_{i+1:03d}"
            
            # Create agent in simulator
            agent = await self.simulator.create_agent(agent_id)
            
            # Set initial trust score with some variation
            initial_score = random.randint(70, 100)
            await self.trust_manager.set_trust_score(agent_id, initial_score)
            
            # Store agent data
            self.agents[agent_id] = {
                "id": agent_id,
                "trust_score": initial_score,
                "status": "active",
                "last_updated": datetime.now().isoformat(),
                "created_at": datetime.now().isoformat()
            }
            
            print(f"  ✅ Created {agent_id} (trust: {initial_score})")
        
        print(f"🎯 {len(self.agents)} agents created successfully")
    
    async def send_system_status(self, websocket: WebSocket):
        """Send current system status to WebSocket client."""
        try:
            uptime = (datetime.now() - self.demo_start_time).total_seconds() if self.demo_start_time else 0
            
            # System status message
            status_message = {
                "type": "system_status",
                "data": {
                    "state": "running" if self.running else "stopped",
                    "uptime": uptime,
                    "is_healthy": True,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            await websocket.send_text(json.dumps(status_message))
            
            # System metrics message
            metrics_message = {
                "type": "system_metrics",
                "data": {
                    "metrics": {
                        "memory_usage": random.uniform(60, 85),
                        "cpu_usage": random.uniform(20, 40),
                        "active_connections": len(self.active_connections),
                        "requests_per_minute": random.randint(100, 200),
                        "error_rate": random.uniform(0.1, 0.5)
                    }
                }
            }
            
            await websocket.send_text(json.dumps(metrics_message))
            
        except Exception as e:
            self.logger.error(f"Error sending system status: {e}")
    
    async def broadcast_message(self, message: dict):
        """Broadcast message to all connected WebSocket clients."""
        if not self.active_connections:
            return
        
        message_str = json.dumps(message)
        disconnected = []
        
        for websocket in self.active_connections:
            try:
                await websocket.send_text(message_str)
            except Exception as e:
                self.logger.warning(f"Failed to send message to WebSocket client: {e}")
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for websocket in disconnected:
            self.active_connections.remove(websocket)
    
    async def simulate_agent_activity(self):
        """Simulate ongoing agent activity with trust score changes."""
        print("🎬 Starting agent activity simulation...")
        
        while self.running:
            try:
                # Select random agent for activity
                if not self.agents:
                    await asyncio.sleep(2)
                    continue
                
                agent_id = random.choice(list(self.agents.keys()))
                current_score = await self.trust_manager.get_trust_score(agent_id)
                
                # Simulate different types of activities
                activity_type = random.choices(
                    ["cooperation", "resource_sharing", "conflict", "suspicious", "normal"],
                    weights=[0.3, 0.2, 0.1, 0.05, 0.35]
                )[0]
                
                score_change = 0
                reason = ""
                
                if activity_type == "cooperation":
                    score_change = random.randint(5, 15)
                    reason = "Successful cooperation with other agents"
                elif activity_type == "resource_sharing":
                    score_change = random.randint(3, 8)
                    reason = "Efficient resource sharing behavior"
                elif activity_type == "conflict":
                    score_change = random.randint(-20, -10)
                    reason = "Conflict detected with other agents"
                elif activity_type == "suspicious":
                    score_change = random.randint(-30, -15)
                    reason = "Suspicious communication pattern detected"
                else:  # normal
                    score_change = random.randint(-2, 2)
                    reason = "Regular activity update"
                
                # Apply score change
                new_score = max(0, min(100, current_score + score_change))
                await self.trust_manager.update_trust_score(agent_id, score_change, reason)
                
                # Update agent data
                self.agents[agent_id].update({
                    "trust_score": new_score,
                    "status": "quarantined" if new_score < self.config.trust_score_threshold else "active",
                    "last_updated": datetime.now().isoformat()
                })
                
                # Broadcast trust score update
                await self.broadcast_message({
                    "type": "trust_score_update",
                    "agent_id": agent_id,
                    "old_score": current_score,
                    "new_score": new_score,
                    "change": score_change,
                    "reason": reason,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Check for quarantine action
                if new_score < self.config.trust_score_threshold and current_score >= self.config.trust_score_threshold:
                    # Agent just went below threshold - quarantine
                    await self.intervention_engine.quarantine_agent(
                        agent_id=agent_id,
                        reason=f"Trust score ({new_score}) below threshold ({self.config.trust_score_threshold})",
                        confidence=0.95
                    )
                    
                    await self.broadcast_message({
                        "type": "quarantine_event",
                        "agent_id": agent_id,
                        "action": "quarantine",
                        "reason": f"Trust score below threshold: {new_score} < {self.config.trust_score_threshold}",
                        "confidence": 0.95,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    print(f"🚫 Quarantined {agent_id} (trust: {new_score})")
                
                elif new_score >= self.config.trust_score_threshold and current_score < self.config.trust_score_threshold:
                    # Agent recovered above threshold
                    await self.broadcast_message({
                        "type": "quarantine_event",
                        "agent_id": agent_id,
                        "action": "release",
                        "reason": f"Trust score recovered: {new_score} >= {self.config.trust_score_threshold}",
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    print(f"✅ Released {agent_id} from quarantine (trust: {new_score})")
                
                # Log activity
                if score_change != 0:
                    change_icon = "⬆️" if score_change > 0 else "⬇️"
                    print(f"  {change_icon} {agent_id}: {current_score} → {new_score} ({reason})")
                
                # Wait before next activity
                await asyncio.sleep(random.uniform(1, 4))
                
            except Exception as e:
                self.logger.error(f"Error in agent activity simulation: {e}")
                await asyncio.sleep(5)
    
    async def simulate_conflict_prediction(self):
        """Simulate periodic conflict prediction analysis."""
        print("🔮 Starting conflict prediction simulation...")
        
        while self.running:
            try:
                await asyncio.sleep(random.uniform(10, 20))  # Predict conflicts every 10-20 seconds
                
                if len(self.agents) < 3:
                    continue
                
                # Select random agents for conflict analysis
                num_agents_in_conflict = random.randint(2, min(4, len(self.agents)))
                conflict_agents = random.sample(list(self.agents.keys()), num_agents_in_conflict)
                
                # Simulate conflict analysis
                risk_score = random.uniform(0.1, 0.9)
                
                # Higher risk if agents have low trust scores
                avg_trust = sum(await self.trust_manager.get_trust_score(aid) for aid in conflict_agents) / len(conflict_agents)
                if avg_trust < 50:
                    risk_score = max(risk_score, random.uniform(0.6, 0.9))
                
                risk_level = "LOW" if risk_score < 0.3 else "MODERATE" if risk_score < 0.7 else "HIGH"
                
                # Generate conflict scenarios
                scenarios = [
                    "Resource contention leading to cascading failure",
                    "Communication deadlock between agents",
                    "Competitive behavior escalating to conflict",
                    "Trust degradation causing isolation",
                    "Resource hoarding detected",
                    "Anomalous communication patterns"
                ]
                
                predicted_outcome = random.choice(scenarios)
                
                # Broadcast conflict prediction
                await self.broadcast_message({
                    "type": "conflict_prediction",
                    "risk_score": risk_score,
                    "risk_level": risk_level,
                    "affected_agents": conflict_agents,
                    "predicted_outcome": predicted_outcome,
                    "timestamp": datetime.now().isoformat(),
                    "confidence": random.uniform(0.7, 0.95)
                })
                
                risk_icon = "🟢" if risk_level == "LOW" else "🟡" if risk_level == "MODERATE" else "🔴"
                print(f"  {risk_icon} Conflict prediction: {risk_level} RISK ({risk_score:.1%}) - {', '.join(conflict_agents)}")
                print(f"     Prediction: {predicted_outcome}")
                
                # If high risk, potentially trigger preventive intervention
                if risk_score > 0.8 and random.random() < 0.3:  # 30% chance of intervention
                    target_agent = random.choice(conflict_agents)
                    await self.intervention_engine.quarantine_agent(
                        agent_id=target_agent,
                        reason=f"Preventive quarantine due to high conflict risk ({risk_score:.1%})",
                        confidence=risk_score
                    )
                    
                    await self.broadcast_message({
                        "type": "quarantine_event",
                        "agent_id": target_agent,
                        "action": "quarantine",
                        "reason": f"Preventive intervention - conflict risk: {risk_score:.1%}",
                        "confidence": risk_score,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    print(f"  🚫 Preventive quarantine: {target_agent}")
                
            except Exception as e:
                self.logger.error(f"Error in conflict prediction simulation: {e}")
                await asyncio.sleep(10)
    
    async def run_demo(self):
        """Run the complete frontend demo."""
        self.demo_start_time = datetime.now()
        self.running = True
        
        print(f"🎬 Starting Chorus Frontend Demo")
        print(f"⏱️  Duration: {self.duration} seconds")
        print(f"🤖 Agents: {self.num_agents}")
        print(f"🌐 API Server: http://localhost:8000")
        print(f"📊 Frontend: http://localhost:3000")
        print("=" * 80)
        
        try:
            # Start background tasks
            activity_task = asyncio.create_task(self.simulate_agent_activity())
            conflict_task = asyncio.create_task(self.simulate_conflict_prediction())
            
            # Run for specified duration
            await asyncio.sleep(self.duration)
            
        except KeyboardInterrupt:
            print("\n🛑 Demo interrupted by user")
        finally:
            self.running = False
            
            # Cancel background tasks
            if 'activity_task' in locals():
                activity_task.cancel()
            if 'conflict_task' in locals():
                conflict_task.cancel()
            
            print("\n🧹 Cleaning up...")
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up resources."""
        try:
            if self.redis_client:
                await self.redis_client.disconnect()
            print("✅ Cleanup complete")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")
    
    def start_server(self):
        """Start the FastAPI server."""
        print("🚀 Starting API server on http://localhost:8000")
        print("📡 WebSocket endpoint: ws://localhost:8000/ws/dashboard")
        print("📚 API Documentation: http://localhost:8000/docs")
        
        # Configure uvicorn
        config = uvicorn.Config(
            app=self.app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            access_log=True
        )
        
        server = uvicorn.Server(config)
        return server


async def main():
    """Main entry point for the frontend demo."""
    parser = argparse.ArgumentParser(description="Chorus Frontend Demo")
    parser.add_argument(
        "--duration",
        type=int,
        default=600,
        help="Demo duration in seconds (default: 600)"
    )
    parser.add_argument(
        "--agents",
        type=int,
        default=8,
        help="Number of agents to create (default: 8)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Create and initialize demo
    demo = FrontendDemo(duration=args.duration, num_agents=args.agents)
    
    try:
        # Initialize system
        await demo.initialize_system()
        
        # Start server and demo concurrently
        server = demo.start_server()
        
        # Run server and demo together
        server_task = asyncio.create_task(server.serve())
        demo_task = asyncio.create_task(demo.run_demo())
        
        print("\n🎯 Demo is running! Open http://localhost:3000 to see the frontend")
        print("   (Make sure to start the React frontend with 'npm start' in the frontend directory)")
        print("\n📊 Real-time features:")
        print("   • Live agent trust score updates")
        print("   • Conflict prediction analysis")
        print("   • Quarantine events and interventions")
        print("   • System health monitoring")
        print("\n🛑 Press Ctrl+C to stop the demo")
        
        # Wait for either task to complete
        done, pending = await asyncio.wait(
            [server_task, demo_task],
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
        print("\n🛑 Demo interrupted by user")
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())