"""
Trust score management system with Redis persistence.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import asdict

from .interfaces import TrustManager, TrustScoreManager
from .models.core import TrustScoreEntry
from .redis_client import redis_client
from ..config import settings
from ..logging_config import get_agent_logger
from ..event_bus import event_bus
from ..integrations.datadog_client import datadog_client


logger = logging.getLogger(__name__)
agent_logger = get_agent_logger(__name__)


class TrustPolicy:
    """
    Configurable trust score adjustment policies.
    
    Defines how trust scores are adjusted based on different agent behaviors
    and system events.
    """
    
    # Default trust score adjustments
    CONFLICT_PENALTY = -10
    COOPERATION_BONUS = 5
    QUARANTINE_PENALTY = -20
    TIMEOUT_PENALTY = -5
    SUCCESSFUL_REQUEST_BONUS = 1
    
    # Trust score bounds
    MIN_SCORE = 0
    MAX_SCORE = 100
    INITIAL_SCORE = 100
    
    # Quarantine threshold
    QUARANTINE_THRESHOLD = 30
    
    @classmethod
    def apply_adjustment(cls, current_score: int, adjustment: int) -> int:
        """
        Apply trust score adjustment with bounds checking.
        
        Args:
            current_score: Current trust score
            adjustment: Adjustment amount (positive or negative)
            
        Returns:
            New trust score within valid bounds
        """
        new_score = current_score + adjustment
        return max(cls.MIN_SCORE, min(cls.MAX_SCORE, new_score))


class RedisTrustScoreManager(TrustScoreManager):
    """
    Redis-based trust score manager implementation.
    
    Manages agent trust scores with persistence, history tracking,
    and configurable adjustment policies.
    """
    
    def __init__(self, redis_client_instance=None, key_prefix: str = "trust_score"):
        """
        Initialize trust score manager.
        
        Args:
            redis_client_instance: Redis client instance (uses global if None)
            key_prefix: Prefix for Redis keys
        """
        self.redis_client = redis_client_instance or redis_client
        self.key_prefix = key_prefix
        self.policy = TrustPolicy()
        
        logger.info("Trust score manager initialized")
    
    def _get_redis_key(self, agent_id: str) -> str:
        """
        Generate Redis key for agent trust score.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Redis key string
        """
        return f"{self.key_prefix}:{agent_id}"
    
    def initialize_agent(self, agent_id: str) -> TrustScoreEntry:
        """
        Initialize trust score for a new agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            New trust score entry
            
        Raises:
            ValueError: If agent already exists
        """
        redis_key = self._get_redis_key(agent_id)
        
        # Check if agent already exists
        if self.redis_client.exists(redis_key):
            raise ValueError(f"Agent {agent_id} already has a trust score")
        
        # Create new trust score entry
        now = datetime.now()
        entry = TrustScoreEntry(
            agent_id=agent_id,
            current_score=self.policy.INITIAL_SCORE,
            last_updated=now,
            adjustment_history=[],
            quarantine_count=0,
            creation_time=now
        )
        
        # Store in Redis
        self.redis_client.set_json(redis_key, asdict(entry))
        
        agent_logger.log_agent_action(
            "INFO",
            f"Initialized trust score for agent {agent_id}",
            agent_id=agent_id,
            action_type="trust_score_init",
            trust_score=self.policy.INITIAL_SCORE
        )
        return entry
    
    def adjust_score(self, agent_id: str, adjustment: int, reason: str) -> TrustScoreEntry:
        """
        Adjust an agent's trust score.
        
        Args:
            agent_id: Agent identifier
            adjustment: Score adjustment (positive or negative)
            reason: Reason for adjustment
            
        Returns:
            Updated trust score entry
            
        Raises:
            ValueError: If agent doesn't exist
        """
        redis_key = self._get_redis_key(agent_id)
        
        # Get existing entry
        entry_data = self.redis_client.get_json(redis_key)
        if entry_data is None:
            raise ValueError(f"Agent {agent_id} not found")
        
        # Reconstruct entry object
        entry = TrustScoreEntry(**entry_data)
        
        # Apply adjustment
        old_score = entry.current_score
        entry.current_score = self.policy.apply_adjustment(old_score, adjustment)
        entry.last_updated = datetime.now()
        
        # Add to adjustment history
        adjustment_record = {
            "timestamp": entry.last_updated.isoformat(),
            "adjustment": adjustment,
            "old_score": old_score,
            "new_score": entry.current_score,
            "reason": reason
        }
        entry.adjustment_history.append(adjustment_record)
        
        # Update quarantine count if this was a quarantine-related adjustment
        if "quarantine" in reason.lower():
            entry.quarantine_count += 1
        
        # Store updated entry
        self.redis_client.set_json(redis_key, asdict(entry))
        
        agent_logger.log_trust_score_update(
            agent_id=agent_id,
            old_score=old_score,
            new_score=entry.current_score,
            adjustment=adjustment,
            reason=reason
        )
        
        # Publish event
        event_bus.publish("trust_score_update", {
            "type": "trust_score_update",
            "agent_id": agent_id,
            "new_score": entry.current_score,
            "old_score": old_score,
            "reason": reason,
            "timestamp": entry.last_updated.isoformat()
        })
        
        # Send observability data to Datadog
        try:
            datadog_client.track_trust_score_change(
                agent_id=agent_id,
                old_score=old_score,
                new_score=entry.current_score,
                reason=reason
            )
        except Exception as e:
            # Don't fail trust score update if observability fails
            logger.warning(f"Failed to send trust score change to Datadog: {e}")
        
        return entry
    
    def get_score_entry(self, agent_id: str) -> Optional[TrustScoreEntry]:
        """
        Get complete trust score entry for an agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Trust score entry or None if not found
        """
        redis_key = self._get_redis_key(agent_id)
        entry_data = self.redis_client.get_json(redis_key)
        
        if entry_data is None:
            return None
        
        return TrustScoreEntry(**entry_data)


class RedisTrustManager(TrustManager):
    """
    Redis-based trust manager implementation.
    
    Provides high-level trust management operations using the trust score manager.
    """
    
    def __init__(self, score_manager: TrustScoreManager = None):
        """
        Initialize trust manager.
        
        Args:
            score_manager: Trust score manager instance (creates default if None)
        """
        self.score_manager = score_manager or RedisTrustScoreManager()
        self.quarantine_threshold = settings.trust_scoring.quarantine_threshold
        
        logger.info(f"Trust manager initialized with quarantine threshold {self.quarantine_threshold}")
    
    def get_trust_score(self, agent_id: str) -> int:
        """
        Get the current trust score for an agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Current trust score (0-100)
            
        Raises:
            ValueError: If agent doesn't exist
        """
        entry = self.score_manager.get_score_entry(agent_id)
        if entry is None:
            # Auto-initialize new agents
            entry = self.score_manager.initialize_agent(agent_id)
        
        return entry.current_score
    
    def update_trust_score(self, agent_id: str, adjustment: int, reason: str) -> None:
        """
        Update an agent's trust score.
        
        Args:
            agent_id: Agent identifier
            adjustment: Score adjustment (positive or negative)
            reason: Reason for adjustment
        """
        try:
            self.score_manager.adjust_score(agent_id, adjustment, reason)
        except ValueError:
            # Auto-initialize new agents
            self.score_manager.initialize_agent(agent_id)
            self.score_manager.adjust_score(agent_id, adjustment, reason)
    
    def check_quarantine_threshold(self, agent_id: str) -> bool:
        """
        Check if an agent should be quarantined based on trust score.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            True if agent should be quarantined, False otherwise
        """
        try:
            current_score = self.get_trust_score(agent_id)
            should_quarantine = current_score < self.quarantine_threshold
            
            if should_quarantine:
                agent_logger.log_agent_action(
                    "WARNING",
                    f"Agent trust score below quarantine threshold",
                    agent_id=agent_id,
                    action_type="quarantine_threshold_breach",
                    trust_score=current_score,
                    context={"threshold": self.quarantine_threshold}
                )
            
            return should_quarantine
        except Exception as e:
            agent_logger.log_system_error(
                e,
                component="trust_manager",
                operation="check_quarantine_threshold",
                agent_id=agent_id
            )
            return False
    
    def get_all_trust_scores(self) -> Dict[str, int]:
        """
        Get trust scores for all agents.
        
        Returns:
            Dictionary mapping agent IDs to trust scores
        """
        # This is a simplified implementation that would need to be enhanced
        # for production use with proper key scanning and pagination
        try:
            # In a real implementation, you'd use Redis SCAN to iterate through keys
            # For now, we'll return an empty dict as this method requires
            # additional Redis operations not implemented in the basic client
            logger.warning("get_all_trust_scores not fully implemented - requires key scanning")
            return {}
        except Exception as e:
            agent_logger.log_system_error(
                e,
                component="trust_manager",
                operation="get_all_trust_scores"
            )
            return {}
            
    def get_all_agent_ids(self) -> List[str]:
        """
        Get all known agent IDs.
        
        Returns:
            List of agent IDs
        """
        try:
            # Scan for keys matching trust_score:*
            # Note: We access the redis client through the score_manager
            cursor = '0'
            keys = []
            prefix = self.score_manager.key_prefix
            match_pattern = f"{prefix}:*"
            
            while cursor != 0:
                cursor, batch = self.score_manager.redis_client._client.scan(cursor=cursor, match=match_pattern, count=100)
                keys.extend(batch)
                
            # Extract agent IDs from keys
            # Key format: trust_score:{agent_id}
            agent_ids = []
            for key in keys:
                # Handle bytes if redis returns bytes
                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                # Remove prefix
                if key_str.startswith(f"{prefix}:"):
                    agent_ids.append(key_str.split(f"{prefix}:")[1])
            
            return agent_ids
            
        except Exception as e:
            agent_logger.log_system_error(
                e,
                component="trust_manager",
                operation="get_all_agent_ids"
            )
            return []
            
    def get_agent_history(self, agent_id: str) -> List[Dict]:
        """
        Get the trust score adjustment history for an agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            List of adjustment records
        """
        entry = self.score_manager.get_score_entry(agent_id)
        if entry:
            return entry.adjustment_history
        return []

    def get_agent_history_in_range(self, agent_id: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Get adjustment history for an agent within a specified time range.
        
        Args:
            agent_id: Agent identifier
            start_date: Start of range
            end_date: End of range
            
        Returns:
            List of adjustment records
        """
        history = self.get_agent_history(agent_id)
        filtered = []
        for item in history:
            try:
                # Handle ISO format string
                ts = datetime.fromisoformat(item["timestamp"])
                # Ensure timezone awareness compatibility if needed, but for simplicity:
                if start_date <= ts <= end_date:
                    filtered.append(item)
            except (ValueError, TypeError):
                continue
        return filtered

    def get_quarantine_count(self, agent_id: str) -> int:
        """
        Get the number of times an agent has been quarantined.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Number of quarantine events for the agent
        """
        entry = self.score_manager.get_score_entry(agent_id)
        if entry is None:
            return 0
        return entry.quarantine_count

    def get_trust_score_analytics(self, agent_id: str) -> Dict[str, float]:
        """
        Get trust score analytics for an agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Dictionary with analytics metrics (trend, volatility, etc.)
        """
        history = self.get_agent_history(agent_id)
        if not history:
            return {"trend": 0.0, "volatility": 0.0, "average_adjustment": 0.0}

        # Extract score snapshots from history
        scores = [item["new_score"] for item in history]
        adjustments = [item["adjustment"] for item in history]
        
        if not scores:
            return {"trend": 0.0, "volatility": 0.0, "average_adjustment": 0.0}

        trend = self._calculate_trend(scores)
        volatility = self._calculate_volatility(scores)
        avg_adj = sum(adjustments) / len(adjustments) if adjustments else 0.0

        return {
            "trend": trend,
            "volatility": volatility,
            "average_adjustment": avg_adj
        }

    def _calculate_trend(self, values: List[float]) -> float:
        """
        Calculate the linear trend (slope) of a series.
        """
        if len(values) < 2:
            return 0.0
        
        n = len(values)
        x = list(range(n))
        y = values
        
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(i * j for i, j in zip(x, y))
        sum_xx = sum(i ** 2 for i in x)
        
        denominator = n * sum_xx - sum_x ** 2
        if denominator == 0:
            return 0.0
            
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        return slope

    def _calculate_volatility(self, values: List[float]) -> float:
        """
        Calculate the volatility (standard deviation) of a series.
        """
        if len(values) < 2:
            return 0.0
            
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1) # Sample std dev
        return variance ** 0.5


# Global trust manager instance
trust_manager = RedisTrustManager(score_manager=RedisTrustScoreManager())