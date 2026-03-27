
import asyncio
import json
import logging
import os
from datetime import datetime

import websockets
from confluent_kafka import Consumer
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Kafka Consumer Configuration ---
load_dotenv(dotenv_path='backend/.env', override=True)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_DECISIONS_TOPIC = os.getenv("KAFKA_AGENT_DECISIONS_TOPIC", "agent-decisions-processed")
KAFKA_ALERTS_TOPIC = os.getenv("KAFKA_SYSTEM_ALERTS_TOPIC", "system-alerts")
KAFKA_MESSAGES_TOPIC = os.getenv("KAFKA_AGENT_MESSAGES_TOPIC", "agent-messages-raw")

consumer_conf = {
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'group.id': 'chorus-frontend-bridge',
    'auto.offset.reset': 'latest'
}

# --- WebSocket Server Configuration ---
CONNECTED_CLIENTS = set()

async def register(websocket):
    """Adds a new client to the set of connected clients."""
    CONNECTED_CLIENTS.add(websocket)
    logger.info(f"New client connected: {websocket.remote_address}")

async def unregister(websocket):
    """Removes a client from the set of connected clients."""
    CONNECTED_CLIENTS.remove(websocket)
    logger.info(f"Client disconnected: {websocket.remote_address}")

async def broadcast(message):
    """Broadcasts a message to all connected clients."""
    if CONNECTED_CLIENTS:
        await asyncio.wait([client.send(message) for client in CONNECTED_CLIENTS])

async def websocket_handler(websocket, path):
    """Handles WebSocket connections."""
    await register(websocket)
    try:
        await websocket.wait_closed()
    finally:
        await unregister(websocket)

async def kafka_consumer():
    """Consumes messages from Kafka and broadcasts them to WebSockets."""
    consumer = Consumer(consumer_conf)
    consumer.subscribe([KAFKA_DECISIONS_TOPIC, KAFKA_ALERTS_TOPIC, KAFKA_MESSAGES_TOPIC])

    logger.info(f"Subscribed to Kafka topics: {KAFKA_DECISIONS_TOPIC}, {KAFKA_ALERTS_TOPIC}, {KAFKA_MESSAGES_TOPIC}")

    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            await asyncio.sleep(0.1)
            continue
        if msg.error():
            logger.error(f"Kafka consumer error: {msg.error()}")
            continue

        try:
            # Decode and parse message
            val_str = msg.value().decode('utf-8')
            try:
                val_json = json.loads(val_str)
            except json.JSONDecodeError:
                val_json = val_str

            topic = msg.topic()
            
            # Wrap based on topic to match Frontend wsClient expectations
            if topic == KAFKA_MESSAGES_TOPIC:
                wrapper = {"type": "universal_traffic", "data": val_json, "timestamp": datetime.now().isoformat()}
            elif topic == KAFKA_DECISIONS_TOPIC:
                wrapper = {"type": "conflict_prediction", "data": val_json, "timestamp": datetime.now().isoformat()}
            elif topic == KAFKA_ALERTS_TOPIC:
                wrapper = {"type": "system_alert", "data": val_json, "timestamp": datetime.now().isoformat()}
            else:
                wrapper = {"type": "kafka_event", "topic": topic, "data": val_json, "timestamp": datetime.now().isoformat()}

            message_data = json.dumps(wrapper)
            logger.info(f"Broadcasting {wrapper['type']} from {topic}: {message_data[:200]}...")
            await broadcast(message_data)
            
        except Exception as e:
            logger.error(f"Error processing Kafka message: {e}")

    consumer.close()


async def main():
    """Starts the WebSocket server and Kafka consumer."""
    websocket_server = websockets.serve(websocket_handler, "localhost", 8000)
    
    logger.info("WebSocket server started on ws://localhost:8000")
    
    # Run the WebSocket server and Kafka consumer concurrently
    await asyncio.gather(
        websocket_server,
        kafka_consumer()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
