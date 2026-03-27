import asyncio
import logging
from ..base import BaseNetworkAdapter, NetworkConfig, ChorusObservation, Intervention
from .client import AgentVerseClient
from .mapper import AgentVerseAdapter as SchemaMapper

logger = logging.getLogger(__name__)

class AgentVerseNetworkAdapter(BaseNetworkAdapter):
    """
    Adapter for the AgentVerse network.
    Uses polling to fetch messages and converts them to ChorusObservations.
    """
    
    def __init__(self, config: NetworkConfig):
        super().__init__(config)
        self.client = AgentVerseClient(api_key=config.api_key)
        self.dedup_prefix = "chorus:av:msg:"
        self.dedup_ttl = 86400
        # Lazy load Redis
        self.redis = None

    async def start(self):
        """Start the polling loop."""
        self.is_running = True
        logger.info(f"AgentVerse Adapter started for {self.config.network_id}")
        
        # Connect to Redis if available (via global client or similar)
        try:
            from ...prediction_engine.redis_client import redis_client
            self.redis = redis_client
        except ImportError:
            logger.warning("Redis client not available for deduplication")

        while self.is_running:
            try:
                await self.poll()
            except Exception as e:
                logger.error(f"Error in AgentVerse polling loop: {e}")
            
            # Non-blocking sleep
            for _ in range(int(self.config.polling_interval * 10)):
                if not self.is_running:
                    break
                await asyncio.sleep(0.1)

    async def stop(self):
        self.is_running = False
        logger.info("AgentVerse Adapter stopped")

    async def poll(self):
        """Fetch and push events."""
        if not self.config.endpoint_url: # reused for Monitored Address
            return

        raw_messages = await self.client.get_mailbox_messages(self.config.endpoint_url, limit=20)
        
        for raw_msg in raw_messages:
            uuid = raw_msg.get("uuid")
            if not uuid:
                continue

            # Deduplication
            if self.redis and self.redis.exists(f"{self.dedup_prefix}{uuid}"):
                continue

            # Map to Internal Message
            chorus_msg = SchemaMapper.to_chorus_message(raw_msg)
            
            # Map to Universal Observation
            observation = ChorusObservation(
                network_id="agentverse",
                event_id=uuid,
                timestamp=chorus_msg.timestamp,
                agent_id=chorus_msg.sender_id,
                event_type=chorus_msg.message_type,
                payload=chorus_msg.content
            )
            
            # Push
            await self.push_observation(observation)

            # Mark processed
            if self.redis:
                try:
                    self.redis.set(f"{self.dedup_prefix}{uuid}", "1", ttl=self.dedup_ttl)
                except Exception:
                    pass

    async def execute_intervention(self, intervention: Intervention) -> bool:
        """
        Execute intervention. 
        AgentVerse doesn't support 'ban' API yet, so we log or send a message.
        """
        logger.info(f"Executing Intervention on AgentVerse: {intervention}")
        # Logic to send 'Stop' message to agent mailbox would go here
        return True
