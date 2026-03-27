import asyncio
import uvicorn
import random
import sys
import os
from datetime import datetime, timezone

# Add current directory to path so we can import src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.api.main import create_app
from src.system_lifecycle import lifecycle_manager
from src.prediction_engine.trust_manager import trust_manager
from src.event_bus import event_bus
from src.prediction_engine.models.alert import ClassifiedAlert, AlertSeverity, AlertContext, ImpactAssessment
from src.prediction_engine.alert_delivery_engine import alert_delivery_engine
from src.integrations.elevenlabs_client import voice_client

# Create app instance
app = create_app(lifecycle_manager)

async def simulate_system_activity():
    """Simulate active agents and system events."""
    print("🚀 Starting Chorus Simulation Engine...")
    
    # Initialize some agents
    agents = [f"agent_{i:03d}" for i in range(1, 10)]
    for agent in agents:
        trust_manager.get_trust_score(agent)

    while True:
        try:
            await asyncio.sleep(random.uniform(0.5, 2.0))
            
            # 1. Simulate Trust Score Updates
            agent = random.choice(agents)
            
            # Determine adjustment based on current score to create interesting patterns
            current = trust_manager.get_trust_score(agent)
            
            reason = "successful_cooperation"
            adj = random.randint(1, 5)
            
            if random.random() < 0.15: 
                # Occasional bad behavior
                adj = random.randint(-15, -5)
                reason = "resource_conflict_detected"
            elif random.random() < 0.05:
                # Critical failure
                adj = -30
                reason = "security_policy_violation"
                
            # This triggers event_bus.publish("trust_score_update") internally in TrustManager
            trust_manager.update_trust_score(agent, adj, reason)
            new_score = current + adj
            print(f"🔹 Updated {agent}: {current} -> {new_score} ({reason})")
            
            # 3. Simulate Quarantine (if score low)
            if new_score < 30:
                event_bus.publish("agent_quarantined", {
                    "type": "quarantine_event",
                    "agent_id": agent,
                    "reason": reason,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                print(f"🚫 Quarantined {agent}")
                
                # Trigger Voice Alert
                alert_context = AlertContext(
                    incident_type="QUARANTINE",
                    affected_agents=[agent],
                    risk_score=0.9,
                    active_quarantines=1,
                    timestamp=datetime.now(timezone.utc)
                )
                impact = ImpactAssessment(
                    system_impact_score=0.8,
                    business_impact_score=0.7,
                    estimated_downtime_minutes=0,
                    affected_services=["agent-network"],
                    description="Agent quarantined due to trust violation"
                )
                alert = ClassifiedAlert(
                    severity=AlertSeverity.CRITICAL,
                    title=f"Agent {agent} Quarantined",
                    description=f"Agent {agent} has been quarantined due to critical trust score drop. Reason: {reason}",
                    impact=impact,
                    recommended_action="Review agent logs and behavior pattern.",
                    requires_voice_alert=True,
                    context=alert_context,
                    timestamp=datetime.now(timezone.utc)
                )
                alert_delivery_engine.process_alert(alert)

            # 4. Simulate Pattern Detection (occasionally)
            if random.random() < 0.1:
                pattern = random.choice(["RESOURCE_HOARDING", "ROUTING_LOOP", "BYZANTINE_BEHAVIOR"])
                severity = "critical" if pattern == "BYZANTINE_BEHAVIOR" else "warning"
                event_bus.publish("decision_update", {
                    "agent_id": agent,
                    "patterns_detected": [pattern],
                    "pattern_details": {
                        pattern: {
                            "severity": severity,
                            "details": f"Detected {pattern} in agent interactions",
                            "affected_agents": [agent, random.choice(agents)]
                        }
                    },
                    "risk_score": 0.8,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                print(f"🔍 Pattern Detected: {pattern}")
                
                if pattern == "BYZANTINE_BEHAVIOR": # Voice alert for critical patterns
                    alert_context = AlertContext(
                        incident_type=pattern,
                        affected_agents=[agent],
                        risk_score=0.95,
                        timestamp=datetime.now(timezone.utc)
                    )
                    impact = ImpactAssessment(
                        system_impact_score=0.9,
                        business_impact_score=0.8,
                        estimated_downtime_minutes=5,
                        affected_services=["network-routing"],
                        description="Byzantine behavior pattern detected"
                    )
                    alert = ClassifiedAlert(
                        severity=AlertSeverity.CRITICAL,
                        title=f"{pattern} Detected",
                        description=f"Critical pattern {pattern} detected originating from agent {agent}.",
                        impact=impact,
                        recommended_action="Isolate agent immediately.",
                        requires_voice_alert=True,
                        context=alert_context,
                        timestamp=datetime.now(timezone.utc)
                    )
                    alert_delivery_engine.process_alert(alert)

            # 2. Simulate Conflict Predictions (occasionally)
            if random.random() < 0.1:
                risk = random.uniform(0.6, 0.95)
                affected = random.sample(agents, 2)
                event_bus.publish("conflict_prediction", {
                    "type": "conflict_prediction",
                    "id": f"conflict_{int(datetime.now().timestamp())}",
                    "risk_score": risk,
                    "affected_agents": affected,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "active"
                })
                print(f"⚠️  Conflict Predicted: Risk {risk:.2f} agents {affected}")
                
            # 5. Simulate System Alerts (occasionally)
            if random.random() < 0.05:
                event_bus.publish("system_alert", {
                    "type": "system_alert",
                    "data": {
                        "severity": "warning",
                        "title": "Network Latency Warning",
                        "description": "High latency detected in mesh network",
                        "script": "Warning: High latency detected in the mesh network.",
                        "impact": {
                            "system": 0.4,
                            "business": 0.2
                        },
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                })

        except Exception as e:
            print(f"❌ Simulation Error: {e}")

@app.post("/demo/trigger/{scenario}")
async def trigger_demo_scenario(scenario: str):
    """
    Manually trigger a specific demo scenario for video recording.
    Options: 'deadlock', 'lazy_loop', 'resource_hog'
    """
    scenario = scenario.lower()
    timestamp = datetime.now(timezone.utc)
    print(f"🎬 Manually Triggering Scenario: {scenario.upper()}")

    if scenario == "deadlock":
        # Simulate Distributed Deadlock
        agents = ["agent_db_lock", "agent_email_service"]
        
        # 0. Update Topology (Visuals)
        # Create circular dependency A -> B -> A
        event_bus.publish("graph_update", {
            "type": "graph_update",
            "data": {
                "event_type": "edge_added",
                "data": { "source": agents[0], "target": agents[1], "interaction_type": "lock_wait" }
            },
            "timestamp": timestamp.isoformat()
        })
        event_bus.publish("graph_update", {
            "type": "graph_update",
            "data": {
                "event_type": "edge_added",
                "data": { "source": agents[1], "target": agents[0], "interaction_type": "lock_wait" }
            },
            "timestamp": timestamp.isoformat()
        })

        # 1. Prediction Event
        event_bus.publish("conflict_prediction", {
            "type": "conflict_prediction",
            "id": f"conflict_{int(timestamp.timestamp())}",
            "risk_score": 0.95,
            "affected_agents": agents,
            "predicted_failure_mode": "Distributed Deadlock (Circular Wait)",
            "timestamp": timestamp.isoformat(),
            "status": "active"
        })
        
        # 2. Critical Alert & Voice
        alert_context = AlertContext(
            incident_type="DEADLOCK",
            affected_agents=agents,
            risk_score=0.95,
            timestamp=timestamp
        )
        impact = ImpactAssessment(
            system_impact_score=0.95,
            business_impact_score=0.9,
            estimated_downtime_minutes=15,
            affected_services=["database", "notifications"],
            description="Circular dependency detected between Database and Email services."
        )
        alert = ClassifiedAlert(
            severity=AlertSeverity.CRITICAL,
            title="Distributed Deadlock Detected",
            description="Agent 'agent_db_lock' and 'agent_email_service' are in a circular wait state. Immediate intervention required.",
            impact=impact,
            recommended_action="Force release locks and restart transaction.",
            requires_voice_alert=True,
            context=alert_context,
            timestamp=timestamp
        )
        alert_delivery_engine.process_alert(alert)
        return {"status": "triggered", "scenario": "deadlock"}

    elif scenario == "lazy_loop":
        # Simulate Lazy Loop (Livelock)
        agents = ["agent_lazy_A", "agent_lazy_B", "agent_lazy_C"]
        
        # 0. Update Topology (Visuals)
        # Create triangle A -> B -> C -> A
        event_bus.publish("graph_update", {
            "type": "graph_update",
            "data": { "event_type": "edge_added", "data": { "source": agents[0], "target": agents[1], "interaction_type": "delegate" } },
            "timestamp": timestamp.isoformat()
        })
        event_bus.publish("graph_update", {
            "type": "graph_update",
            "data": { "event_type": "edge_added", "data": { "source": agents[1], "target": agents[2], "interaction_type": "delegate" } },
            "timestamp": timestamp.isoformat()
        })
        event_bus.publish("graph_update", {
            "type": "graph_update",
            "data": { "event_type": "edge_added", "data": { "source": agents[2], "target": agents[0], "interaction_type": "delegate" } },
            "timestamp": timestamp.isoformat()
        })

        # 1. Prediction Event
        event_bus.publish("conflict_prediction", {
            "type": "conflict_prediction",
            "id": f"conflict_{int(timestamp.timestamp())}",
            "risk_score": 0.88,
            "affected_agents": agents,
            "predicted_failure_mode": "Infinite Routing Loop (Livelock)",
            "timestamp": timestamp.isoformat(),
            "status": "active"
        })
        
        # 2. Critical Alert & Voice
        alert_context = AlertContext(
            incident_type="ROUTING_LOOP",
            affected_agents=agents,
            risk_score=0.88,
            timestamp=timestamp
        )
        impact = ImpactAssessment(
            system_impact_score=0.7,
            business_impact_score=0.5,
            estimated_downtime_minutes=0,
            affected_services=["task-router"],
            description="Agents delegating task in circular pattern without execution."
        )
        alert = ClassifiedAlert(
            severity=AlertSeverity.WARNING,
            title="Lazy Loop Detected",
            description="Infinite delegation loop detected: A -> B -> C -> A. Token usage high, progress zero.",
            impact=impact,
            recommended_action="Quarantine agents and reroute task to Supervisor.",
            requires_voice_alert=True,
            context=alert_context,
            timestamp=timestamp
        )
        alert_delivery_engine.process_alert(alert)
        return {"status": "triggered", "scenario": "lazy_loop"}
        
    elif scenario == "resource_hog":
        agent = "agent_miner_01"
        # Quarantine Event
        event_bus.publish("agent_quarantined", {
            "type": "quarantine_event",
            "agent_id": agent,
            "reason": "cryptomining_signature_detected",
            "timestamp": timestamp.isoformat()
        })
        return {"status": "triggered", "scenario": "resource_hog"}

    return {"status": "error", "message": "Unknown scenario"}

@app.on_event("startup")
async def start_system():
    print("Initializing System Lifecycle...")
    if not lifecycle_manager.startup():
        print("❌ System startup failed!")
    else:
        print("✅ System started successfully")
    
    # Enable voice for demo
    voice_client.enabled = True
    print("🔊 Voice Alerts Enabled (Simulation Mode)")
    alert_delivery_engine.start()

@app.on_event("startup")
async def start_simulation_task():
    asyncio.create_task(simulate_system_activity())

@app.on_event("shutdown")
async def stop_system():
    print("Shutting down System Lifecycle...")
    alert_delivery_engine.stop()
    lifecycle_manager.shutdown()

if __name__ == "__main__":
    print("Starting Demo Backend on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
