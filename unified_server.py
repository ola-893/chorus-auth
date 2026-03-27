
import asyncio
import json
import logging
import os
import sys
from datetime import datetime

print("--- UNIFIED SERVER SCRIPT STARTING ---")

import uvicorn
import websockets
from confluent_kafka import Consumer
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Ensure the source directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))
# Load environment variables from backend/.env
load_dotenv(dotenv_path='backend/.env', override=True)


from src.api.main import create_app
from src.config import load_settings
from src.system_lifecycle import SystemLifecycleManager

# --- Basic Configuration ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Kafka Consumer Configuration ---
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_DECISIONS_TOPIC = os.getenv("KAFKA_AGENT_DECISIONS_TOPIC", "agent-decisions-processed")
KAFKA_ALERTS_TOPIC = os.getenv("KAFKA_SYSTEM_ALERTS_TOPIC", "system-alerts")

consumer_conf = {
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'group.id': 'chorus-unified-server-demo-replay',
    'auto.offset.reset': 'earliest'
}

# --- WebSocket Connection Manager ---
from typing import List

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# --- Kafka Consumer Logic ---
async def kafka_consumer_logic():
    """Consumes messages from Kafka and broadcasts them via WebSocket."""
    consumer = Consumer(consumer_conf)
    consumer.subscribe([KAFKA_DECISIONS_TOPIC, KAFKA_ALERTS_TOPIC])
    logger.info(f"Subscribed to Kafka topics: {[KAFKA_DECISIONS_TOPIC, KAFKA_ALERTS_TOPIC]}")
    
    while True:
        # Poll with 0 timeout to avoid blocking the asyncio event loop
        msg = consumer.poll(0.0)
        if msg is None:
            await asyncio.sleep(0.1)
            continue
        if msg.error():
            logger.error(f"Kafka consumer error: {msg.error()}")
            continue
        
        try:
            message_data = msg.value().decode('utf-8')
            logger.info(f"Received from Kafka topic '{msg.topic()}': {message_data}")
            await manager.broadcast(message_data)
        except Exception as e:
            logger.error(f"Error processing/broadcasting Kafka message: {e}")

# --- Create and Configure FastAPI App ---
def create_unified_app():
    # 1. Load settings and initialize lifecycle manager
    settings = load_settings()
    lifecycle_manager = SystemLifecycleManager(settings)
    
    # 2. Create the core FastAPI application
    app = create_app(lifecycle_manager)
    
    # 3. Add CORS middleware to allow frontend requests
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("CORS middleware configured for http://localhost:3000")

    # 4. Add WebSocket endpoint
    @app.websocket("/ws/dashboard")
    async def websocket_endpoint(websocket: WebSocket):
        await manager.connect(websocket)
        try:
            while True:
                # Keep the connection alive
                await websocket.receive_text()
        except WebSocketDisconnect:
            manager.disconnect(websocket)
            logger.info("Client disconnected.")

    # 4.1 Add Event Injection endpoint (Fallback for Kafka failures)
    from fastapi import Request
    @app.post("/inject-event")
    async def inject_event(request: Request):
        data = await request.json()
        logger.info(f"Received injected event: {data}")
        await manager.broadcast(json.dumps(data))
        return {"status": "ok"}

    # 5. Register startup event to run Kafka consumer
    @app.on_event("startup")
    async def startup_event():
        logger.info("Application startup...")
        # Start the system lifecycle
        lifecycle_manager.startup()
        # Start Kafka consumer in the background
        asyncio.create_task(kafka_consumer_logic())
        logger.info("Kafka consumer task created.")
        
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Application shutdown...")
        lifecycle_manager.shutdown()

    return app

app = create_unified_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
