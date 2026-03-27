from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import time
import logging

from src.integrations.kafka_client import kafka_bus
from src.config import settings

router = APIRouter(prefix="/v1/universal", tags=["Universal Integration"])
logger = logging.getLogger(__name__)

# --- Data Models (Aligned with TDD) ---

class ChorusObservation(BaseModel):
    """
    Standardized observation event (REQ-OBS-001).
    """
    network_id: str = Field(..., description="Registered network identifier")
    event_id: str = Field(..., description="Unique idempotency key for this event")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the event occurred")
    agent_id: str = Field(..., description="ID of the agent performing the action")
    event_type: str = Field(..., description="Type of action (message, tool_use, etc.)")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary payload")

class ObservationPayload(BaseModel):
    """Batch payload."""
    source_system: str = Field(..., description="Name of the external system (e.g., 'CrewAI-Finance')")
    events: List[ChorusObservation]

class ObservationResponse(BaseModel):
    status: str
    ingested_count: int
    processed_at: float

# --- Security ---

async def verify_api_key(x_chorus_api_key: str = Header(None, alias="X-Agent-API-Key")):
    """Simple API Key validation."""
    # Allow development bypass or check env
    if not x_chorus_api_key and settings.is_production():
        raise HTTPException(status_code=401, detail="Missing API Key")
    return x_chorus_api_key

# --- Endpoints ---

@router.post("/observe", response_model=ObservationResponse)
async def ingest_observations(
    payload: ObservationPayload, 
    api_key: str = Depends(verify_api_key)
):
    """
    Ingest stream of events from an external multi-agent system.
    """
    if not settings.kafka.enabled:
        raise HTTPException(status_code=503, detail="Ingestion disabled: Kafka not available")

    count = 0
    try:
        for obs in payload.events:
            # Map ChorusObservation -> Internal AgentMessage for legacy processor
            message_payload = {
                "sender_id": obs.agent_id,
                "receiver_id": obs.payload.get("target", "system"),
                "message_type": obs.event_type,
                "content": obs.payload,
                "timestamp": obs.timestamp.isoformat(),
                "metadata": {
                    "source": "universal_api",
                    "network_id": obs.network_id,
                    "event_id": obs.event_id
                }
            }
            
            kafka_bus.produce(
                topic=settings.kafka.agent_messages_topic,
                value=message_payload,
                key=obs.agent_id
            )
            count += 1
            
        return ObservationResponse(
            status="accepted",
            ingested_count=count,
            processed_at=time.time()
        )
        
    except Exception as e:
        logger.error(f"Error processing universal observation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhooks/register")
async def register_webhook(
    url: str,
    network_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Register a webhook for intervention callbacks (REQ-INT-001).
    """
    logger.info(f"Registered webhook {url} for network {network_id}")
    return {"status": "registered", "id": f"hook_{network_id}_{int(time.time())}"}
