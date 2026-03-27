#!/usr/bin/env python3
print("DEBUG: Script starting...", flush=True)
import os
import sys
import time
import subprocess
import logging
import asyncio
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ChorusLauncher")

def check_redis():
    """Check if Redis is running, start via Docker if not."""
    logger.info("🔍 Checking Redis availability...")
    try:
        # Try to connect using python-redis
        import redis
        r = redis.Redis(host='localhost', port=6379, socket_timeout=1)
        if r.ping():
            logger.info("✅ Redis is already running and accessible.")
            return True
    except (ImportError, redis.exceptions.ConnectionError):
        pass

    # Redis not accessible, check Docker
    logger.info("⚠️  Redis not responding. Checking Docker...")
    try:
        # Check if container exists
        result = subprocess.run(["docker", "ps", "-a", "--filter", "name=chorus-redis", "--format", "{{.Names}}"], capture_output=True, text=True)
        container_exists = "chorus-redis" in result.stdout.strip()
        
        if container_exists:
            # Check if running
            result = subprocess.run(["docker", "ps", "--filter", "name=chorus-redis", "--format", "{{.Names}}"], capture_output=True, text=True)
            if "chorus-redis" in result.stdout.strip():
                logger.info("✅ Redis container 'chorus-redis' is running.")
                return True
            else:
                logger.info("🔄 Starting existing 'chorus-redis' container...")
                subprocess.run(["docker", "start", "chorus-redis"], check=True)
                time.sleep(2) # Wait for startup
                return True
        else:
            # Run new container
            logger.info("🚀 Starting new Redis container 'chorus-redis'...")
            subprocess.run(["docker", "run", "-d", "--name", "chorus-redis", "-p", "6379:6379", "redis:alpine"], check=True)
            time.sleep(2) # Wait for startup
            return True
            
    except Exception as e:
        logger.error(f"❌ Failed to manage Redis via Docker: {e}")
        return False

def setup_environment():
    """Load environment variables."""
    # Add backend to path
    backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
    sys.path.append(backend_path)

def main():
    print("""
    =======================================================
       CHORUS: AGENT IMMUNE SYSTEM - HACKATHON LAUNCHER
    =======================================================
    Partners: Google Cloud, Datadog, Confluent, ElevenLabs
    """)
    
    setup_environment()
    
    if not check_redis():
        print("\n❌ CRITICAL: Redis is required but could not be started.")
        print("Please run: docker run -d -p 6379:6379 redis:alpine")
        sys.exit(1)
        
    print("\n✅ Infrastructure Ready.")
    print("🚀 Launching Comprehensive Demo...")
    time.sleep(1)
    
    try:
        # Ensure backend is in path so 'src' imports work
        backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
        if backend_dir not in sys.path:
            sys.path.append(backend_dir)

        import importlib.util
        # Force import from current directory to avoid conflict with backend/comprehensive_demo.py
        spec = importlib.util.spec_from_file_location("root_comprehensive_demo", os.path.join(os.path.dirname(os.path.abspath(__file__)), "comprehensive_demo.py"))
        comprehensive_demo = importlib.util.module_from_spec(spec)
        sys.modules["root_comprehensive_demo"] = comprehensive_demo
        spec.loader.exec_module(comprehensive_demo)
        ComprehensiveDemo = comprehensive_demo.ComprehensiveDemo
        
        from src.integrations.kafka_client import kafka_bus
        from src.event_bus import event_bus
        from src.config import settings
        import json

        # Ensure log directory exists
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'demo_events.jsonl')

        # --- Kafka Forwarder Setup ---
        def forward_to_kafka(data):
            """Forward local events to Kafka and local log."""
            print(f"DEBUG: Kafka Bridge received event: {data.get('type') or 'unknown'}", flush=True)
            
            # Local logging for immediate verification
            try:
                with open(log_file, 'a') as f:
                    f.write(json.dumps(data) + '\n')
            except Exception as e:
                logger.error(f"Failed to log event locally: {e}")

            if not settings.kafka.enabled:
                return
            try:
                def delivery_report(err, msg):
                    if err is not None:
                        logger.error(f"Message delivery failed: {err}")
                    else:
                        logger.info(f"Message delivered to {msg.topic()} [{msg.partition()}]")

                # Use agent_decisions_topic as a general event channel for the demo
                topic = settings.kafka.agent_decisions_topic
                logger.info(f"Producing to Kafka topic {topic}: {str(data)[:100]}...")
                kafka_bus.produce(topic, data)
                # Manually poll to trigger delivery reports
                if hasattr(kafka_bus, 'producer') and kafka_bus.producer:
                    kafka_bus.producer.poll(0)
            except Exception as e:
                logger.error(f"Failed to forward event to Kafka: {e}")

        # Subscribe to critical events
        logger.info("🔗 Bridging simulation events to Kafka...")
        event_bus.subscribe("trust_score_update", forward_to_kafka)
        event_bus.subscribe("conflict_prediction", forward_to_kafka)
        event_bus.subscribe("system_alert", forward_to_kafka)
        event_bus.subscribe("agent_quarantined", forward_to_kafka)
        event_bus.subscribe("intervention_executed", forward_to_kafka)
        event_bus.subscribe("voice_alert_generated", forward_to_kafka)
        
        # ALSO subscribe to the demo's specific event bus instance in case of path mismatch
        if hasattr(comprehensive_demo, 'event_bus'):
            logger.info("🔗 Bridging root_comprehensive_demo event_bus...")
            comprehensive_demo.event_bus.subscribe("trust_score_update", forward_to_kafka)
            comprehensive_demo.event_bus.subscribe("conflict_prediction", forward_to_kafka)
            comprehensive_demo.event_bus.subscribe("system_alert", forward_to_kafka)
            comprehensive_demo.event_bus.subscribe("agent_quarantined", forward_to_kafka)
            comprehensive_demo.event_bus.subscribe("intervention_executed", forward_to_kafka)
            comprehensive_demo.event_bus.subscribe("voice_alert_generated", forward_to_kafka)
        # -----------------------------
        
        # Initialize and run
        demo = ComprehensiveDemo()
        print("\n🎤 Starting Continuous Demo (Technical Audience)...", flush=True)
        
        async def run_wrapper():
            await demo.initialize_system()
            while True:
                print("\n🎬 Starting new demo cycle...", flush=True)
                await demo.run_demo()
                print("\n⏳ Cycle complete. Pausing before next run...", flush=True)
                await asyncio.sleep(5)
            
        asyncio.run(run_wrapper())
        
        # Ensure messages are sent
        logger.info("Flushing Kafka producer...")
        kafka_bus.flush(timeout=5.0)
        
    except KeyboardInterrupt:
        print("\n👋 Demo stopped by user.")
    except ImportError as e:
        print(f"\n❌ Error importing demo components: {e}")
        print("Make sure you are running from the project root and dependencies are installed.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
