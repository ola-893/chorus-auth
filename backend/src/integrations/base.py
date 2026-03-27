from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class NetworkConfig(BaseModel):
    """Configuration for a network adapter."""
    network_id: str
    api_key: Optional[str] = None
    endpoint_url: Optional[str] = None
    webhook_url: Optional[str] = None
    polling_interval: float = 30.0

class ChorusObservation(BaseModel):
    """Standardized observation event."""
    network_id: str
    event_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    agent_id: str
    event_type: str
    payload: Dict[str, Any]

class Intervention(BaseModel):
    """Intervention command from Chorus."""
    intervention_id: str
    target_agent_id: str
    action: str  # QUARANTINE, THROTTLE, ALERT
    reason: str
    duration: Optional[int] = None

class BaseNetworkAdapter(ABC):
    """
    Abstract Base Class for all Network Adapters.
    Implements the Strategy Pattern for multi-network support.
    """
    
    def __init__(self, config: NetworkConfig):
        self.config = config
        self.is_running = False

    @abstractmethod
    async def start(self):
        """Start polling or subscribing to the network's event stream."""
        pass

    @abstractmethod
    async def stop(self):
        """Gracefully shut down the adapter."""
        pass

    @abstractmethod
    async def execute_intervention(self, intervention: Intervention) -> bool:
        """
        Execute a Chorus directive on the network.
        Returns True if successful.
        """
        pass

    async def push_observation(self, observation: ChorusObservation):
        """
        Push a normalized observation to the Chorus Core.
        In a distributed setup, this might HTTP POST to /v1/observe.
        In a monolith, this might write directly to Kafka.
        """
        # For the hackathon monolith, we import the bus directly.
        # Ideally, this should be dependency injected.
        from .kafka_client import kafka_bus
        from ..config import settings
        
        kafka_bus.produce(
            topic=settings.kafka.agent_messages_topic,
            value=observation.dict(),
            key=observation.agent_id
        )
