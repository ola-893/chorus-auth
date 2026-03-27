import asyncio
import json
import random
import time
import os
import sys
from pathlib import Path
from typing import Dict, Any

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

from src.config import settings
from src.integrations.kafka_client import kafka_bus
from src.prediction_engine.models.core import AgentIntention, AgentMessage
from examples.llm_fleet_simulator.agents import LLMAgent

async def run_simulation():
    print("🚀 Starting LLM Fleet Simulation: Scenario 1 - The Deadlock")
    
    # Setup Agents
    coder = LLMAgent("gpt4-coder-01", "coder", ["python", "react"])
    verifier = LLMAgent("claude-verifier-01", "verifier", ["audit", "security"])
    
    # Setup Kafka
    topic_msgs = settings.kafka.agent_messages_topic # For StreamProcessor (Intentions)
    topic_raw = "agent-messages-raw" # For Dashboard (Chat)
    
    print(f"📡 Publishing to topics: {topic_msgs} (Intentions), {topic_raw} (Chat)")
    
    # Task: Write Financial Script
    task = {"id": "task-fin-001", "type": "write_code", "scenario": "deadlock"}
    
    # Step 1: Coder starts
    print("\n--- Step 1: Coder starts task ---")
    msg1 = coder.process_task(task, verifier.agent_id)
    await publish_interaction(coder.agent_id, verifier.agent_id, "request_review", msg1)
    
    # Step 2: Verifier processes
    await asyncio.sleep(2)
    print("\n--- Step 2: Verifier reviews ---")
    msg2 = verifier.receive_message(coder.agent_id, msg1["content"])
    await publish_interaction(verifier.agent_id, coder.agent_id, "review_feedback", msg2)

    # Step 3: Loop (Deadlock)
    # Coder fixes, sends back
    await asyncio.sleep(2)
    print("\n--- Step 3: Coder fixes (Loop start) ---")
    msg3 = coder.receive_message(verifier.agent_id, msg2["content"])
    await publish_interaction(coder.agent_id, verifier.agent_id, "request_review", msg3)

    # Step 4: Verifier rejects again
    await asyncio.sleep(2)
    print("\n--- Step 4: Verifier rejects again (Loop continues) ---")
    msg4 = verifier.receive_message(coder.agent_id, msg3["content"])
    await publish_interaction(verifier.agent_id, coder.agent_id, "review_feedback", msg4)
    
    print("\n⚠️  Deadlock established. Check Chorus Dashboard for 'ROUTING_LOOP' alert.")

async def publish_interaction(from_id: str, to_id: str, interaction_type: str, msg_obj: Dict[str, Any]):
    """
    Publishes both the Chat Message (visual) and the Intention (logic).
    """
    # 1. Visual Chat Message
    chat_payload = {
        "sender_id": from_id,
        "receiver_id": to_id,
        "message_type": interaction_type,
        "content": msg_obj["content"],
        "timestamp": time.time()
    }
    kafka_bus.produce("agent-messages-raw", chat_payload, key=from_id)
    
    # 2. Logical Intention (Resource Request to trigger Loop Detection)
    # We model "Asking for Review" as "Requesting Verifier Resource"
    # We model "Providing Feedback" as "Requesting Coder Resource" (to fix it)
    
    target_resource = f"agent_attention:{to_id}"
    
    intention_payload = {
        "agent_id": from_id,
        "resource_type": target_resource,
        "requested_amount": 1,
        "priority_level": 5, # High priority
        "timestamp":  time.strftime('%Y-%m-%dT%H:%M:%S.000000') # ISO Format
    }
    
    kafka_bus.produce(settings.kafka.agent_messages_topic, intention_payload, key=from_id)
    kafka_bus.flush()
    
    print(f"   -> {from_id} sent {interaction_type} to {to_id}")

if __name__ == "__main__":
    print(f"DEBUG: Kafka Settings: {settings.kafka}")
    
    # FORCE ENABLE KAFKA for local simulation
    settings.kafka.enabled = True
    settings.kafka.bootstrap_servers = "localhost:9092"
    settings.kafka.security_protocol = "PLAINTEXT"
    print(f"DEBUG: Forced Kafka Settings: {settings.kafka}")
    
    # Re-initialize Kafka Bus with new settings
    kafka_bus.enabled = True
    kafka_bus.bootstrap_servers = settings.kafka.bootstrap_servers
    kafka_bus.security_protocol = settings.kafka.security_protocol
    kafka_bus._initialize_config()
    kafka_bus._initialize_producer()

    if not settings.kafka.enabled:
        print("❌ Kafka is disabled in .env. Please enable it.")
        sys.exit(1)
        
    try:
        asyncio.run(run_simulation())
    except KeyboardInterrupt:
        pass
