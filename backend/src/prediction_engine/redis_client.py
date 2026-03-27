"""
Redis client implementation with connection pooling and retry logic.
"""
import json
import logging
import time
from typing import Optional, Dict, Any
import redis
from redis.connection import ConnectionPool
from redis.exceptions import ConnectionError, TimeoutError, RedisError

from ..config import settings
from ..logging_config import get_agent_logger
from ..error_handling import (
    handle_redis_errors,
    retry_with_exponential_backoff,
    redis_circuit_breaker,
    system_recovery_context
)


logger = logging.getLogger(__name__)
agent_logger = get_agent_logger(__name__)


class RedisClient:
    """
    Redis client with connection pooling, retry logic, and exponential backoff.
    
    Provides robust Redis operations with automatic reconnection and error handling
    for trust score storage and retrieval.
    """
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        password: str = None,
        db: int = None,
        max_connections: int = 10,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
        retry_on_timeout: bool = True,
        health_check_interval: int = 30
    ):
        """
        Initialize Redis client with connection pooling.
        
        Args:
            host: Redis server host (defaults to config)
            port: Redis server port (defaults to config)
            password: Redis password (defaults to config)
            db: Redis database number (defaults to config)
            max_connections: Maximum connections in pool
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Connection timeout in seconds
            retry_on_timeout: Whether to retry on timeout
            health_check_interval: Health check interval in seconds
        """
        self.host = host or settings.redis.host
        self.port = port or settings.redis.port
        self.password = password or settings.redis.password
        self.db = db or settings.redis.db
        
        # Connection pool configuration
        self.pool = ConnectionPool(
            host=self.host,
            port=self.port,
            password=self.password,
            db=self.db,
            max_connections=max_connections,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            retry_on_timeout=retry_on_timeout,
            health_check_interval=health_check_interval
        )
        
        # Redis client instance
        self._client = redis.Redis(connection_pool=self.pool)
        
        # Retry configuration
        self.max_retries = 3
        self.base_delay = 0.1  # Base delay for exponential backoff
        self.max_delay = 2.0   # Maximum delay between retries
        
        logger.info(f"Redis client initialized for {self.host}:{self.port}")
    
    def _execute_with_retry(self, operation, *args, **kwargs):
        """
        Execute Redis operation with exponential backoff retry logic.
        
        Args:
            operation: Redis operation function to execute
            *args: Arguments for the operation
            **kwargs: Keyword arguments for the operation
            
        Returns:
            Result of the Redis operation
            
        Raises:
            RedisError: If all retry attempts fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return operation(*args, **kwargs)
            except (ConnectionError, TimeoutError) as e:
                last_exception = e
                
                if attempt == self.max_retries:
                    agent_logger.log_system_error(
                        e,
                        component="redis_client",
                        operation="execute_with_retry",
                        context={"max_retries": self.max_retries, "operation": operation.__name__}
                    )
                    raise RedisError(f"Redis operation failed: {e}") from e
                
                # Calculate exponential backoff delay
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                
                logger.warning(
                    f"Redis operation failed (attempt {attempt + 1}/{self.max_retries + 1}), "
                    f"retrying in {delay:.2f}s: {e}"
                )
                
                time.sleep(delay)
            except RedisError as e:
                agent_logger.log_system_error(
                    e,
                    component="redis_client",
                    operation="execute_with_retry",
                    context={"error_type": "non_recoverable"}
                )
                raise
        
        # This should never be reached, but just in case
        raise RedisError(f"Unexpected error in retry logic: {last_exception}")
    
    @redis_circuit_breaker
    @handle_redis_errors
    def get(self, key: str) -> Optional[str]:
        """
        Get a value from Redis.
        
        Args:
            key: Redis key to retrieve
            
        Returns:
            Value as string, or None if key doesn't exist
            
        Raises:
            RedisError: If Redis operation fails after retries
        """
        try:
            result = self._execute_with_retry(self._client.get, key)
            return result.decode('utf-8') if result else None
        except Exception as e:
            logger.error(f"Failed to get key '{key}': {e}")
            raise RedisError(f"Get operation failed for key '{key}': {e}") from e
    
    @redis_circuit_breaker
    @handle_redis_errors
    def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """
        Set a value in Redis.
        
        Args:
            key: Redis key to set
            value: Value to store
            ttl: Time to live in seconds (optional)
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            RedisError: If Redis operation fails after retries
        """
        try:
            if ttl:
                result = self._execute_with_retry(self._client.setex, key, ttl, value)
            else:
                result = self._execute_with_retry(self._client.set, key, value)
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to set key '{key}': {e}")
            raise RedisError(f"Set operation failed for key '{key}': {e}") from e
    
    def delete(self, key: str) -> bool:
        """
        Delete a key from Redis.
        
        Args:
            key: Redis key to delete
            
        Returns:
            True if key was deleted, False if key didn't exist
            
        Raises:
            RedisError: If Redis operation fails after retries
        """
        try:
            result = self._execute_with_retry(self._client.delete, key)
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to delete key '{key}': {e}")
            raise RedisError(f"Delete operation failed for key '{key}': {e}") from e
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in Redis.
        
        Args:
            key: Redis key to check
            
        Returns:
            True if key exists, False otherwise
            
        Raises:
            RedisError: If Redis operation fails after retries
        """
        try:
            result = self._execute_with_retry(self._client.exists, key)
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to check existence of key '{key}': {e}")
            raise RedisError(f"Exists operation failed for key '{key}': {e}") from e
    
    def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get a JSON value from Redis and parse it.
        
        Args:
            key: Redis key to retrieve
            
        Returns:
            Parsed JSON as dictionary, or None if key doesn't exist
            
        Raises:
            RedisError: If Redis operation fails or JSON parsing fails
        """
        try:
            value = self.get(key)
            if value is None:
                return None
            return json.loads(value)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON for key '{key}': {e}")
            raise RedisError(f"JSON parsing failed for key '{key}': {e}") from e
    
    def set_json(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Set a JSON value in Redis.
        
        Args:
            key: Redis key to set
            value: Dictionary to store as JSON
            ttl: Time to live in seconds (optional)
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            RedisError: If Redis operation fails or JSON serialization fails
        """
        try:
            json_value = json.dumps(value, default=str)  # default=str handles datetime objects
            return self.set(key, json_value, ttl)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize JSON for key '{key}': {e}")
            raise RedisError(f"JSON serialization failed for key '{key}': {e}") from e
    
    def ping(self) -> bool:
        """
        Test Redis connection.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            result = self._execute_with_retry(self._client.ping)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get Redis connection information.
        
        Returns:
            Dictionary with connection details
        """
        return {
            "host": self.host,
            "port": self.port,
            "db": self.db,
            "pool_size": self.pool.max_connections,
            "created_connections": self.pool.created_connections,
            "available_connections": len(self.pool._available_connections),
            "in_use_connections": len(self.pool._in_use_connections)
        }
    
    def close(self):
        """
        Close Redis connection pool.
        """
        try:
            self.pool.disconnect()
            logger.info("Redis connection pool closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection pool: {e}")


# Global Redis client instance
redis_client = RedisClient()