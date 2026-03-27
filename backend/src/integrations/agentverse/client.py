import os
import httpx
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

class AgentVerseClient:
    """
    Client for interacting with the AgentVerse API (Almanac and Mailbox).
    """

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://agentverse.ai"):
        self.api_key = api_key or os.getenv("AGENTVERSE_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if not self.api_key:
            logger.warning("AgentVerse API Key not found. Client will fail on authenticated endpoints.")

    async def get_agents(self) -> List[Dict[str, Any]]:
        """
        Retrieves a list of registered agents for the authenticated user.
        Endpoint: GET /v2/agents
        """
        url = f"{self.base_url}/v2/agents"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.headers, timeout=10.0)
                response.raise_for_status()
                # Response is typically a list of agent objects
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"AgentVerse API Error {e.response.status_code}: {e.response.text}")
                raise
            except httpx.RequestError as e:
                logger.error(f"AgentVerse Connection Error: {str(e)}")
                raise

    async def search_agents(self, query_text: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Searches for agents in the public Almanac.
        Endpoint: POST /v1/almanac/search
        """
        url = f"{self.base_url}/v1/almanac/search"
        payload = {
            "text": query_text,
            "limit": limit
        }
        
        async with httpx.AsyncClient() as client:
            try:
                # Almanac search is usually public, but we send headers if we have them
                response = await client.post(url, json=payload, headers=self.headers, timeout=10.0)
                if response.status_code == 404:
                    return []
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.warning(f"Almanac search failed: {e}")
                return []

    async def get_mailbox_messages(self, agent_address: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Fetches messages from the agent's mailbox.
        Endpoint: GET /v2/agents/:address/mailbox
        """
        url = f"{self.base_url}/v2/agents/{agent_address}/mailbox"
        params = {"limit": limit, "offset": offset}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.headers, params=params, timeout=10.0)
                response.raise_for_status()
                # The API returns a list of StoredEnvelope objects directly or wrapped? 
                # Docs say "list all messages...". Assuming direct list or { "data": [...] }
                # Based on standard AgentVerse responses, it's often a direct list or paginated object.
                # We'll return the raw JSON for the adapter to handle.
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"AgentVerse API Error {e.response.status_code}: {e.response.text}")
                raise
            except httpx.RequestError as e:
                logger.error(f"AgentVerse Connection Error: {str(e)}")
                raise

    async def resolve_address(self, address: str) -> Optional[Dict[str, Any]]:
        """
        Resolves an agent address to its details (name, etc.) via Almanac.
        Endpoint: GET /v1/almanac/agents/:address (Hypothetical standard based on docs)
        Actually, docs mentioned: GET /almanac/resolve/:identifier
        """
        # Note: Almanac API structure varies, using the one found in docs search: /v1/almanac/resolve
        # If strict endpoint is different, we adjust.
        # Docs search said: GET /almanac/resolve/:identifier
        url = f"{self.base_url}/v1/almanac/resolve/{address}"
        
        async with httpx.AsyncClient() as client:
            try:
                # Almanac often doesn't need auth for public resolution, but we send headers anyway
                response = await client.get(url, headers=self.headers, timeout=5.0)
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.warning(f"Failed to resolve address {address}: {e}")
                return None
