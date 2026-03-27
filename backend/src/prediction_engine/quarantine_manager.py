"""
Quarantine management system for isolating problematic agents.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import asdict
import threading

from .interfaces import QuarantineManager as QuarantineManagerInterface, AgentNetwork
from .models.core import QuarantineResult, QuarantineAction
from .redis_client import redis_client
from ..config import settings
from ..logging_config import get_agent_logger

from ..event_bus import event_bus

logger = logging.getLogger(__name__)
agent_logger = get_agent_logger(__name__)


class RedisQuarantineManager(QuarantineManagerInterface):
    """
    Redis-based quarantine manager for agent isolation.
    
    Manages quarantine state, enforcement, and logging with persistence
    to Redis for durability across system restarts.
    """
    
    def __init__(self, redis_client_instance=None, key_prefix: str = "quarantine"):
        """
        Initialize quarantine manager.
        
        Args:
            redis_client_instance: Redis client instance (uses global if None)
            key_prefix: Prefix for Redis keys
        """
        self.redis_client = redis_client_instance or redis_client
        self.key_prefix = key_prefix
        self.agent_network: Optional[AgentNetwork] = None
        self.quarantine_lock = threading.Lock()
        
        # Quarantine tracking
        self.quarantined_agents: Set[str] = set()
        self.quarantine_actions: List[QuarantineAction] = []
        
        # Load existing quarantine state from Redis
        self._load_quarantine_state()
        
        logger.info("Quarantine manager initialized")
    
    def set_agent_network(self, agent_network: AgentNetwork) -> None:
        """Set the agent network for quarantine enforcement."""
        self.agent_network = agent_network
    
    def _get_quarantine_key(self, agent_id: str) -> str:
        """Generate Redis key for agent quarantine status."""
        return f"{self.key_prefix}:status:{agent_id}"
    
    def _get_action_key(self, action_id: str) -> str:
        """Generate Redis key for quarantine action."""
        return f"{self.key_prefix}:action:{action_id}"
    
    def _get_agent_list_key(self) -> str:
        """Generate Redis key for quarantined agents list."""
        return f"{self.key_prefix}:agents"
    
    def _load_quarantine_state(self) -> None:
        """Load existing quarantine state from Redis."""
        try:
            # Load quarantined agents list
            agents_data = self.redis_client.get(self._get_agent_list_key())
            if agents_data:
                import json
                self.quarantined_agents = set(json.loads(agents_data))
                logger.info(f"Loaded {len(self.quarantined_agents)} quarantined agents from Redis")
            
        except Exception as e:
            logger.error(f"Error loading quarantine state from Redis: {e}")
            self.quarantined_agents = set()
    
    def _save_quarantine_state(self) -> None:
        """Save quarantine state to Redis."""
        try:
            import json
            agents_json = json.dumps(list(self.quarantined_agents))
            self.redis_client.set(self._get_agent_list_key(), agents_json)
            
        except Exception as e:
            logger.error(f"Error saving quarantine state to Redis: {e}")
    
    def quarantine_agent(self, agent_id: str, reason: str) -> QuarantineResult:
        """
        Quarantine a specific agent.
        
        Args:
            agent_id: Agent to quarantine
            reason: Reason for quarantine
            
        Returns:
            Result of quarantine operation
        """
        with self.quarantine_lock:
            try:
                # Check if already quarantined
                if agent_id in self.quarantined_agents:
                    logger.warning(f"Agent {agent_id} is already quarantined")
                    return QuarantineResult(
                        success=True,
                        agent_id=agent_id,
                        reason="Agent already quarantined",
                        timestamp=datetime.now()
                    )
                
                # Create quarantine action record
                action = QuarantineAction(
                    agent_id=agent_id,
                    reason=reason,
                    timestamp=datetime.now(),
                    duration=None,  # Indefinite quarantine
                    trust_score_before=0,  # Will be updated by caller
                    trust_score_after=0    # Will be updated by caller
                )
                
                # Store quarantine status in Redis
                quarantine_data = {
                    "agent_id": agent_id,
                    "reason": reason,
                    "timestamp": action.timestamp.isoformat(),
                    "active": True
                }
                self.redis_client.set_json(self._get_quarantine_key(agent_id), quarantine_data)
                
                # Store action record
                action_id = f"{agent_id}_{int(action.timestamp.timestamp())}"
                self.redis_client.set_json(self._get_action_key(action_id), asdict(action))
                
                # Only add to quarantined set after successful Redis operations
                self.quarantined_agents.add(agent_id)
                
                # Update quarantined agents list
                self._save_quarantine_state()
                
                # Enforce quarantine on the actual agent if network is available
                if self.agent_network:
                    self._enforce_quarantine(agent_id)
                
                # Add to local action history
                self.quarantine_actions.append(action)
                
                # Keep only recent actions (last 100)
                if len(self.quarantine_actions) > 100:
                    self.quarantine_actions = self.quarantine_actions[-100:]
                
                agent_logger.log_quarantine_action(
                    agent_id=agent_id,
                    action="quarantine",
                    reason=reason,
                    success=True,
                    context={"timestamp": action.timestamp.isoformat()}
                )
                
                # Publish event
                event_bus.publish("agent_quarantined", {
                    "agent_id": agent_id,
                    "reason": reason,
                    "timestamp": action.timestamp.isoformat()
                })
                
                return QuarantineResult(
                    success=True,
                    agent_id=agent_id,
                    reason=f"Successfully quarantined: {reason}",
                    timestamp=action.timestamp
                )
                
            except Exception as e:
                agent_logger.log_system_error(
                    e,
                    component="quarantine_manager",
                    operation="quarantine_agent",
                    agent_id=agent_id,
                    context={"reason": reason}
                )
                return QuarantineResult(
                    success=False,
                    agent_id=agent_id,
                    reason=f"Quarantine failed: {str(e)}",
                    timestamp=datetime.now()
                )
    
    def _enforce_quarantine(self, agent_id: str) -> None:
        """
        Enforce quarantine on the actual agent instance.
        
        Args:
            agent_id: Agent to enforce quarantine on
        """
        try:
            if not self.agent_network:
                logger.warning("No agent network available for quarantine enforcement")
                return
            
            # Find the agent in the network
            active_agents = self.agent_network.get_active_agents()
            target_agent = None
            
            for agent in active_agents:
                if agent.agent_id == agent_id:
                    target_agent = agent
                    break
            
            if target_agent:
                # Set quarantine flag on the agent
                target_agent.quarantine()
                logger.info(f"Enforced quarantine on agent {agent_id}")
            else:
                logger.warning(f"Agent {agent_id} not found in active agents for quarantine enforcement")
                
        except Exception as e:
            logger.error(f"Error enforcing quarantine on agent {agent_id}: {e}")
    
    def is_quarantined(self, agent_id: str) -> bool:
        """
        Check if an agent is currently quarantined.
        
        Args:
            agent_id: Agent to check
            
        Returns:
            True if agent is quarantined, False otherwise
        """
        try:
            # Check local cache first
            if agent_id in self.quarantined_agents:
                return True
            
            # Check Redis for persistent state
            quarantine_data = self.redis_client.get_json(self._get_quarantine_key(agent_id))
            if quarantine_data and quarantine_data.get("active", False):
                # Update local cache
                self.quarantined_agents.add(agent_id)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking quarantine status for agent {agent_id}: {e}")
            return False
    
    def release_quarantine(self, agent_id: str) -> QuarantineResult:
        """
        Release an agent from quarantine.
        
        Args:
            agent_id: Agent to release
            
        Returns:
            Result of release operation
        """
        with self.quarantine_lock:
            try:
                # Check if agent is quarantined
                if agent_id not in self.quarantined_agents:
                    logger.info(f"Agent {agent_id} is not quarantined")
                    return QuarantineResult(
                        success=True,
                        agent_id=agent_id,
                        reason="Agent was not quarantined",
                        timestamp=datetime.now()
                    )
                
                # Remove from quarantined set
                self.quarantined_agents.discard(agent_id)
                
                # Update Redis status
                quarantine_data = self.redis_client.get_json(self._get_quarantine_key(agent_id))
                if quarantine_data:
                    quarantine_data["active"] = False
                    quarantine_data["released_at"] = datetime.now().isoformat()
                    self.redis_client.set_json(self._get_quarantine_key(agent_id), quarantine_data)
                
                # Update quarantined agents list
                self._save_quarantine_state()
                
                # Release quarantine on the actual agent if network is available
                if self.agent_network:
                    self._release_agent_quarantine(agent_id)
                
                agent_logger.log_quarantine_action(
                    agent_id=agent_id,
                    action="release",
                    reason="manual_release",
                    success=True
                )
                
                return QuarantineResult(
                    success=True,
                    agent_id=agent_id,
                    reason="Successfully released from quarantine",
                    timestamp=datetime.now()
                )
                
            except Exception as e:
                logger.exception(f"Error releasing quarantine for agent {agent_id}: {e}")
                return QuarantineResult(
                    success=False,
                    agent_id=agent_id,
                    reason=f"Release failed: {str(e)}",
                    timestamp=datetime.now()
                )
    
    def _release_agent_quarantine(self, agent_id: str) -> None:
        """
        Release quarantine on the actual agent instance.
        
        Args:
            agent_id: Agent to release quarantine on
        """
        try:
            if not self.agent_network:
                logger.warning("No agent network available for quarantine release")
                return
            
            # Find the agent in the network (search all agents, not just active ones)
            all_agents = self.agent_network.agents
            target_agent = None
            
            for agent in all_agents:
                if agent.agent_id == agent_id:
                    target_agent = agent
                    break
            
            if target_agent:
                # Release quarantine flag on the agent
                target_agent.release_quarantine()
                logger.info(f"Released quarantine on agent {agent_id}")
            else:
                logger.warning(f"Agent {agent_id} not found in agent network for quarantine release")
                
        except Exception as e:
            logger.error(f"Error releasing quarantine on agent {agent_id}: {e}")
    
    def get_quarantined_agents(self) -> List[str]:
        """
        Get list of currently quarantined agents.
        
        Returns:
            List of quarantined agent IDs
        """
        return list(self.quarantined_agents)
    
    def get_quarantine_history(self, agent_id: Optional[str] = None) -> List[QuarantineAction]:
        """
        Get quarantine action history.
        
        Args:
            agent_id: Optional agent ID to filter by
            
        Returns:
            List of quarantine actions
        """
        if agent_id:
            return [action for action in self.quarantine_actions if action.agent_id == agent_id]
        return self.quarantine_actions.copy()
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get quarantine statistics.
        
        Returns:
            Dictionary with quarantine statistics
        """
        return {
            "currently_quarantined": len(self.quarantined_agents),
            "total_quarantine_actions": len(self.quarantine_actions),
            "unique_agents_quarantined": len(set(action.agent_id for action in self.quarantine_actions))
        }
    
    def cleanup_expired_quarantines(self, max_age_hours: int = 24) -> int:
        """
        Clean up expired quarantine records.
        
        Args:
            max_age_hours: Maximum age in hours for quarantine records
            
        Returns:
            Number of records cleaned up
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            cleaned_count = 0
            
            # Clean up local action history
            original_count = len(self.quarantine_actions)
            self.quarantine_actions = [
                action for action in self.quarantine_actions 
                if action.timestamp > cutoff_time
            ]
            cleaned_count = original_count - len(self.quarantine_actions)
            
            logger.info(f"Cleaned up {cleaned_count} expired quarantine records")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired quarantines: {e}")
            return 0


# Global quarantine manager instance
quarantine_manager = RedisQuarantineManager()