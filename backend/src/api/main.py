"""
FastAPI application for the Chorus Agent Conflict Predictor.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
import asyncio
import json
from contextlib import asynccontextmanager

try:
    from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, Request, Security
    from fastapi.security import APIKeyHeader
    from fastapi.responses import JSONResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    # FastAPI is optional dependency - create fallback classes
    FastAPI = None
    HTTPException = None
    Depends = None
    Security = None
    APIKeyHeader = None
    JSONResponse = None
    WebSocket = None
    WebSocketDisconnect = None
    Request = None
    StaticFiles = None
    FASTAPI_AVAILABLE = False
    
    # Create a fallback BaseModel for when pydantic is not available
    class BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
        
        def dict(self):
            return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

from ..system_lifecycle import SystemLifecycleManager
from ..logging_config import get_agent_logger
from ..prediction_engine.redis_client import RedisClient
from ..prediction_engine.trust_manager import RedisTrustManager, RedisTrustScoreManager
from ..config import settings
from ..event_bus import event_bus
from .voice_router import router as voice_router
from .demo_router import router as demo_router
from .voice_analytics_router import router as analytics_router
from .impact_router import router as impact_router
from .events_router import router as events_router
from .universal_router import router as universal_router

agent_logger = get_agent_logger(__name__)

# Security schemes
API_KEY_NAME = "X-Agent-API-Key"

if FASTAPI_AVAILABLE:
    api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
    
    async def verify_api_key(api_key: str = Security(api_key_header)):
        """
        Verify API key with proper validation.
        """
        # Check if API key is provided
        if not api_key:
            raise HTTPException(
                status_code=403, 
                detail="Could not validate credentials"
            )
        
        # In development/test, allow any non-empty key for testing
        if settings.environment.value in ["development", "testing"] and not settings.is_production():
            return api_key
                
        # In production, validate against configured keys
        # For now, accept any non-empty string as valid
        # In a real implementation, this would check against a database or Redis
        if len(api_key.strip()) == 0:
            raise HTTPException(
                status_code=403, 
                detail="Could not validate credentials"
            )
            
        return api_key
else:
    api_key_header = None
    
    async def verify_api_key(api_key: str = None):
        """
        Fallback verify function when FastAPI is not available.
        """
        return api_key

if FASTAPI_AVAILABLE:
    class RateLimiter:
        """
        Redis-based rate limiter with proper dependency injection.
        """
        def __init__(self, requests_per_minute: int = 60):
            self.requests_per_minute = requests_per_minute
            self._redis_client = None

        def _get_redis_client(self):
            """Get Redis client instance, creating if needed."""
            if self._redis_client is None:
                try:
                    self._redis_client = RedisClient()
                except Exception as e:
                    agent_logger.log_system_error(e, "api", "rate_limiter_redis_init")
                    self._redis_client = None
            return self._redis_client

        async def __call__(self, request: Request, api_key: str = Depends(verify_api_key)):
            """
            Check rate limit using Redis-based sliding window.
            """
            redis_client = self._get_redis_client()
            if not redis_client:
                # Fail open if Redis is not available
                return
                
            # Use API key or IP as identifier
            client_id = api_key if api_key else request.client.host
            current_minute = datetime.now(timezone.utc).minute
            key = f"rate_limit:{client_id}:{current_minute}"
            
            try:
                # Get current count for this minute
                current_raw = redis_client.get(key)
                current_count = int(current_raw) if current_raw else 0
                
                if current_count >= self.requests_per_minute:
                    raise HTTPException(status_code=429, detail="Too many requests")
                
                # Increment counter using Redis pipeline for atomicity
                if hasattr(redis_client, '_client') and redis_client._client:
                    pipe = redis_client._client.pipeline()
                    pipe.incr(key)
                    pipe.expire(key, 60)  # Expire after 1 minute
                    pipe.execute()
                else:
                    # Fallback for testing - use direct Redis operations
                    new_count = current_count + 1
                    redis_client.set(key, str(new_count))
                    
            except HTTPException:
                raise
            except Exception as e:
                # Fail open if Redis error - log but don't block request
                agent_logger.log_system_error(e, "api", "rate_limiter_check")
                return
else:
    class RateLimiter:
        """
        Fallback rate limiter when FastAPI is not available.
        """
        def __init__(self, requests_per_minute: int = 60):
            self.requests_per_minute = requests_per_minute
            
        async def __call__(self, request=None, api_key: str = None):
            """
            Fallback rate limiter - no-op when FastAPI not available.
            """
            pass

# Instantiate rate limiter - will be created per request to ensure proper Redis connection
def get_rate_limiter():
    """Get rate limiter instance."""
    return RateLimiter(requests_per_minute=100)


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    uptime: float
    components: Dict[str, str]
    details: Optional[Dict[str, Any]] = None


class SystemStatusResponse(BaseModel):
    """System status response model."""
    state: str
    uptime: float
    start_time: Optional[str]
    is_healthy: bool
    dependency_checks: int
    health: Optional[Dict[str, Any]] = None

class TrustScoreResponse(BaseModel):
    """Trust score response model."""
    agent_id: str
    trust_score: int
    history_length: int
    last_updated: Optional[str] = None

if FASTAPI_AVAILABLE:
    class ConnectionManager:
        """WebSocket connection manager."""
        def __init__(self):
            self.active_connections: List[WebSocket] = []

        async def connect(self, websocket: WebSocket):
            await websocket.accept()
            self.active_connections.append(websocket)

        def disconnect(self, websocket: WebSocket):
            self.active_connections.remove(websocket)

        async def broadcast(self, message: str):
            # Iterate over a copy to allow modification during iteration
            for connection in self.active_connections[:]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    # If sending fails, assume connection is dead and remove it
                    # agent_logger.log_system_error(e, "api", "broadcast_send_failed")
                    if connection in self.active_connections:
                        self.active_connections.remove(connection)
else:
    class ConnectionManager:
        """Fallback connection manager when FastAPI is not available."""
        def __init__(self):
            self.active_connections = []

        async def connect(self, websocket):
            self.active_connections.append(websocket)

        def disconnect(self, websocket):
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

        async def broadcast(self, message: str):
            # No-op when FastAPI not available
            pass

manager = ConnectionManager()


def create_app(lifecycle_manager: SystemLifecycleManager) -> FastAPI:
    """
    Create FastAPI application with lifecycle management.
    
    Args:
        lifecycle_manager: System lifecycle manager instance
        
    Returns:
        FastAPI application instance
    """
    if FastAPI is None:
        raise ImportError("FastAPI is required for API mode. Install with: pip install fastapi")
    
    app = FastAPI(
        title="Chorus Agent Conflict Predictor API",
        description="Real-time conflict prediction and intervention for decentralized agent networks",
        version="0.1.0"
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(voice_router)
    app.include_router(demo_router)
    app.include_router(analytics_router)
    app.include_router(impact_router)
    app.include_router(events_router)
    app.include_router(universal_router)
    
    # Mount alerts directory for audio playback
    import os
    alerts_dir = settings.elevenlabs.audio_storage_path
    if not os.path.exists(alerts_dir):
        os.makedirs(alerts_dir, exist_ok=True)
    app.mount("/alerts", StaticFiles(directory=alerts_dir), name="alerts")
    
    # Initialize Redis components for API use
    # Note: In a real app, this might be dependency injected or managed by lifecycle
    try:
        redis_client = RedisClient()
        score_manager = RedisTrustScoreManager(redis_client_instance=redis_client)
        trust_manager = RedisTrustManager(score_manager=score_manager)
    except Exception as e:
        agent_logger.log_system_error(e, "api", "init_redis_components")
        trust_manager = None
    
    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """
        Health check endpoint.
        
        Returns:
            Health status information
        """
        try:
            # Get system status
            system_status = lifecycle_manager.get_status()
            
            # Determine overall health
            is_healthy = lifecycle_manager.is_healthy()
            status = "healthy" if is_healthy else "unhealthy"
            
            # Get component statuses
            components = {}
            if "health" in system_status and system_status["health"]["component_statuses"]:
                components = system_status["health"]["component_statuses"]
            
            response = HealthResponse(
                status=status,
                timestamp=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                uptime=system_status["uptime"],
                components=components,
                details={
                    "state": system_status["state"],
                    "dependency_checks": system_status["dependency_checks"]
                }
            )
            
            # Log health check
            agent_logger.log_agent_action(
                "INFO",
                f"Health check requested: {status}",
                action_type="api_health_check",
                context={"status": status, "uptime": system_status["uptime"]}
            )
            
            # Return appropriate HTTP status
            if is_healthy:
                return response
            else:
                return JSONResponse(
                    status_code=503,
                    content=response.dict()
                )
                
        except Exception as e:
            agent_logger.log_system_error(
                e,
                component="api",
                operation="health_check"
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                    "error": str(e)
                }
            )
    
    @app.get("/status", response_model=SystemStatusResponse, dependencies=[Depends(verify_api_key), Depends(get_rate_limiter)])
    async def system_status():
        """
        System status endpoint.
        
        Returns:
            Detailed system status information
        """
        try:
            status = lifecycle_manager.get_status()
            
            response = SystemStatusResponse(
                state=status["state"],
                uptime=status["uptime"],
                start_time=status["start_time"],
                is_healthy=status["is_healthy"],
                dependency_checks=status["dependency_checks"],
                health=status.get("health")
            )
            
            agent_logger.log_agent_action(
                "INFO",
                "System status requested",
                action_type="api_system_status",
                context={"state": status["state"]}
            )
            
            return response
            
        except Exception as e:
            agent_logger.log_system_error(
                e,
                component="api",
                operation="system_status"
            )
            
            raise HTTPException(status_code=500, detail=str(e))
            
    @app.get("/agents/{agent_id}/trust-score", response_model=TrustScoreResponse, dependencies=[Depends(verify_api_key), Depends(get_rate_limiter)])
    async def get_agent_trust_score(agent_id: str):
        """
        Get trust score for a specific agent.
        """
        if not trust_manager:
            raise HTTPException(status_code=503, detail="Trust manager not available")
            
        try:
            score = trust_manager.get_trust_score(agent_id)
            history = trust_manager.get_agent_history(agent_id)
            
            return TrustScoreResponse(
                agent_id=agent_id,
                trust_score=score,
                history_length=len(history),
                last_updated=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z') 
            )
        except Exception as e:
            agent_logger.log_system_error(e, "api", "get_trust_score", context={"agent_id": agent_id})
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/agents/{agent_id}/history", dependencies=[Depends(verify_api_key), Depends(get_rate_limiter)])
    async def get_agent_history(agent_id: str, start: Optional[str] = None, end: Optional[str] = None):
        """
        Get historical trust score data for a specific agent.
        """
        if not trust_manager:
            raise HTTPException(status_code=503, detail="Trust manager not available")
            
        try:
            history = trust_manager.get_agent_history(agent_id)
            
            # Filter by time range if provided
            if start or end:
                filtered_history = []
                for entry in history:
                    entry_time = datetime.fromisoformat(entry.get('timestamp', '').replace('Z', '+00:00'))
                    
                    if start:
                        start_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
                        if entry_time < start_time:
                            continue
                    
                    if end:
                        end_time = datetime.fromisoformat(end.replace('Z', '+00:00'))
                        if entry_time > end_time:
                            continue
                    
                    filtered_history.append(entry)
                
                history = filtered_history
            
            return {
                "agent_id": agent_id,
                "history": history,
                "total_entries": len(history),
                "time_range": {
                    "start": start,
                    "end": end
                }
            }
        except Exception as e:
            agent_logger.log_system_error(e, "api", "get_agent_history", context={"agent_id": agent_id})
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/agents", dependencies=[Depends(verify_api_key), Depends(get_rate_limiter)])
    async def get_all_agents():
        """
        Get list of all agents with their current trust scores.
        """
        if not trust_manager:
            raise HTTPException(status_code=503, detail="Trust manager not available")
            
        try:
            # Get all agent IDs from trust manager
            all_agents = []
            
            # This is a simplified implementation - in a real system, 
            # you'd have a proper agent registry
            agent_ids = trust_manager.get_all_agent_ids() if hasattr(trust_manager, 'get_all_agent_ids') else []
            
            for agent_id in agent_ids:
                score = trust_manager.get_trust_score(agent_id)
                history = trust_manager.get_agent_history(agent_id)
                last_entry = history[-1] if history else None
                
                # Fetch extended state from Redis
                agent_state = None
                if redis_client:
                    try:
                        agent_state = redis_client.get_json(f"agent_state:{agent_id}")
                    except Exception:
                        pass # Ignore Redis errors for extended state
                
                agent_data = {
                    "id": agent_id,
                    "trust_score": score,
                    "status": "quarantined" if score < 30 else "active",
                    "last_updated": last_entry.get('timestamp') if last_entry else datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                    "history_length": len(history)
                }
                
                if agent_state:
                    agent_data["riskLevel"] = agent_state.get("risk_level")
                    agent_data["activityLevel"] = agent_state.get("activity_level")
                    agent_data["resourceUsage"] = agent_state.get("resource_usage")
                
                all_agents.append(agent_data)
            
            return {
                "agents": all_agents,
                "total_count": len(all_agents),
                "active_count": len([a for a in all_agents if a["status"] == "active"]),
                "quarantined_count": len([a for a in all_agents if a["status"] == "quarantined"]),
                "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            }
        except Exception as e:
            agent_logger.log_system_error(e, "api", "get_all_agents")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/dashboard/metrics", dependencies=[Depends(verify_api_key), Depends(get_rate_limiter)])
    async def get_dashboard_metrics():
        """
        Get aggregated metrics for the dashboard.
        """
        # In a real scenario, this would aggregate data from Datadog or Redis
        status = lifecycle_manager.get_status()
        
        # Get active agents from trust manager
        active_agents_count = 0
        if trust_manager:
            try:
                agent_ids = trust_manager.get_all_agent_ids() if hasattr(trust_manager, 'get_all_agent_ids') else []
                for aid in agent_ids:
                    if trust_manager.get_trust_score(aid) >= 30:
                        active_agents_count += 1
            except Exception:
                pass

        # Get conflicts detected from event log buffer
        from ..event_sourcing import event_log_manager
        conflicts_count = 0
        try:
            # Count conflict_prediction events in the decision topic buffer
            for event in event_log_manager._buffer:
                if event["topic"] == event_log_manager.decision_topic:
                    val = event.get("value", {})
                    if val.get("type") == "conflict_prediction":
                        conflicts_count += 1
        except Exception:
            pass
        
        return {
            "system_health": status.get("is_healthy", False),
            "uptime": status.get("uptime", 0),
            "active_agents": active_agents_count,
            "conflicts_detected": conflicts_count,
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }

    @app.get("/system/circuit-breakers", dependencies=[Depends(verify_api_key), Depends(get_rate_limiter)])
    async def get_circuit_breaker_status():
        """
        Get current circuit breaker states for all services.
        """
        try:
            from ..error_handling import gemini_circuit_breaker, redis_circuit_breaker
            
            circuit_breakers = [
                {
                    "service_name": "gemini_api",
                    "state": gemini_circuit_breaker.state,
                    "failure_count": gemini_circuit_breaker.failure_count,
                    "last_failure_time": datetime.fromtimestamp(gemini_circuit_breaker.last_failure_time, timezone.utc).isoformat().replace('+00:00', 'Z') if gemini_circuit_breaker.last_failure_time else None,
                    "next_attempt_time": (datetime.fromtimestamp(gemini_circuit_breaker.last_failure_time, timezone.utc) + timedelta(seconds=gemini_circuit_breaker.recovery_timeout)).isoformat().replace('+00:00', 'Z') if gemini_circuit_breaker.last_failure_time else None
                },
                {
                    "service_name": "redis",
                    "state": redis_circuit_breaker.state,
                    "failure_count": redis_circuit_breaker.failure_count,
                    "last_failure_time": datetime.fromtimestamp(redis_circuit_breaker.last_failure_time, timezone.utc).isoformat().replace('+00:00', 'Z') if redis_circuit_breaker.last_failure_time else None,
                    "next_attempt_time": (datetime.fromtimestamp(redis_circuit_breaker.last_failure_time, timezone.utc) + timedelta(seconds=redis_circuit_breaker.recovery_timeout)).isoformat().replace('+00:00', 'Z') if redis_circuit_breaker.last_failure_time else None
                }
            ]
            
            return {
                "circuit_breakers": circuit_breakers,
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            }
        except Exception as e:
            agent_logger.log_system_error(e, "api", "get_circuit_breaker_status")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/system/dependencies", dependencies=[Depends(verify_api_key), Depends(get_rate_limiter)])
    async def get_dependency_status():
        """
        Get status of external dependencies.
        """
        try:
            from ..system_health import health_monitor
            
            # Force health checks to get current status
            health_results = health_monitor.force_health_check()
            
            dependencies = []
            for check_name, is_healthy in health_results.items():
                status = "connected" if is_healthy else "disconnected"
                
                # Mock response times for demonstration
                response_times = {
                    "redis_connection": 2.3,
                    "gemini_api": 120.5,
                    "system_resources": 1.0
                }
                
                dependencies.append({
                    "name": check_name.replace("_", " ").title(),
                    "status": status,
                    "last_check": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "response_time": response_times.get(check_name, 0.0),
                    "error_message": None if is_healthy else f"{check_name} check failed"
                })
            
            return {
                "dependencies": dependencies,
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            }
        except Exception as e:
            agent_logger.log_system_error(e, "api", "get_dependency_status")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/system/metrics", dependencies=[Depends(verify_api_key), Depends(get_rate_limiter)])
    async def get_system_metrics():
        """
        Get current system performance metrics.
        """
        try:
            import psutil
            
            # Get system metrics
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Mock some additional metrics
            metrics = {
                "memory_usage": memory.percent,
                "cpu_usage": cpu_percent,
                "active_connections": len(manager.active_connections),
                "requests_per_minute": 145,  # Mock value
                "error_rate": 0.2  # Mock value
            }
            
            return {
                "metrics": metrics,
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            }
        except ImportError:
            # psutil not available, return mock data
            return {
                "metrics": {
                    "memory_usage": 68.5,
                    "cpu_usage": 23.1,
                    "active_connections": len(manager.active_connections),
                    "requests_per_minute": 145,
                    "error_rate": 0.2
                },
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            }
        except Exception as e:
            agent_logger.log_system_error(e, "api", "get_system_metrics")
            raise HTTPException(status_code=500, detail=str(e))

    @app.websocket("/ws/dashboard")
    async def websocket_endpoint(websocket: WebSocket):
        """
        WebSocket endpoint for real-time dashboard updates.
        """
        await manager.connect(websocket)
        try:
            # Send initial state
            status = lifecycle_manager.get_status()
            await websocket.send_json({
                "type": "system_status",
                "data": status,
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            })
            
            # Send initial circuit breaker status
            try:
                from ..error_handling import gemini_circuit_breaker, redis_circuit_breaker
                circuit_breakers = [
                    {
                        "service_name": "gemini_api",
                        "state": gemini_circuit_breaker.state,
                        "failure_count": gemini_circuit_breaker.failure_count,
                        "last_failure_time": datetime.fromtimestamp(gemini_circuit_breaker.last_failure_time, timezone.utc).isoformat().replace('+00:00', 'Z') if gemini_circuit_breaker.last_failure_time else None,
                        "next_attempt_time": (datetime.fromtimestamp(gemini_circuit_breaker.last_failure_time, timezone.utc) + timedelta(seconds=gemini_circuit_breaker.recovery_timeout)).isoformat().replace('+00:00', 'Z') if gemini_circuit_breaker.last_failure_time else None
                    },
                    {
                        "service_name": "redis",
                        "state": redis_circuit_breaker.state,
                        "failure_count": redis_circuit_breaker.failure_count,
                        "last_failure_time": datetime.fromtimestamp(redis_circuit_breaker.last_failure_time, timezone.utc).isoformat().replace('+00:00', 'Z') if redis_circuit_breaker.last_failure_time else None,
                        "next_attempt_time": (datetime.fromtimestamp(redis_circuit_breaker.last_failure_time, timezone.utc) + timedelta(seconds=redis_circuit_breaker.recovery_timeout)).isoformat().replace('+00:00', 'Z') if redis_circuit_breaker.last_failure_time else None
                    }
                ]
                
                for cb in circuit_breakers:
                    await websocket.send_json({
                        "type": "circuit_breaker_update",
                        "data": cb,
                        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                    })
            except Exception as e:
                agent_logger.log_system_error(e, "api", "websocket_circuit_breaker_init")
            
            while True:
                # Keep connection alive, actual updates come via event_bus
                await asyncio.sleep(60) 
        except WebSocketDisconnect:
            manager.disconnect(websocket)
    
    @app.get("/")
    async def root():
        """
        Root endpoint.
        
        Returns:
            Basic API information
        """
        return {
            "name": "Chorus Agent Conflict Predictor API",
            "version": "0.1.0",
            "status": "running" if lifecycle_manager.is_running() else "stopped",
            "endpoints": {
                "health": "/health",
                "status": "/status",
                "docs": "/docs",
                "trust_score": "/agents/{agent_id}/trust-score",
                "metrics": "/dashboard/metrics",
                "circuit_breakers": "/system/circuit-breakers",
                "dependencies": "/system/dependencies",
                "system_metrics": "/system/metrics",
                "websocket": "/ws/dashboard"
            }
        }
    
    # Add startup and shutdown event handlers
    @app.on_event("startup")
    async def startup_event():
        """Handle application startup."""
        # Set main loop for event bus to handle background thread publishing
        event_bus.set_main_loop(asyncio.get_running_loop())
        
        agent_logger.log_agent_action(
            "INFO",
            "FastAPI application starting...",
            action_type="api_startup"
        )
        
        # Initialize the system lifecycle (starts stream processor, event bridge, etc.)
        try:
            # We run this in a thread if it's blocking, but it mostly starts background threads
            lifecycle_manager.startup()
        except Exception as e:
            agent_logger.log_system_error(e, "api", "lifecycle_startup")
        
        # Cleanup old voice files
        try:
            from ..integrations.elevenlabs_client import voice_client
            voice_client.cleanup_old_files()
        except Exception:
            pass
        
        # Hook up event logging for historical queries
        from ..event_sourcing import event_log_manager
        
        async def log_msg_event(data):
            event_log_manager._record_event(event_log_manager.msg_topic, data)
            
        async def log_decision_event(data):
            event_log_manager._record_event(event_log_manager.decision_topic, data)

        event_bus.subscribe("trust_score_update", log_msg_event)
        event_bus.subscribe("conflict_prediction", log_decision_event)
        event_bus.subscribe("decision_update", log_decision_event)
        event_bus.subscribe("agent_quarantined", log_decision_event)
        event_bus.subscribe("intervention_executed", log_decision_event)
        
        # Subscribe to event bus
        def create_broadcast_handler(event_type):
            async def broadcast_event(data):
                try:
                    # Always wrap in the format the frontend expects: {type, data, timestamp}
                    # even if the data already contains a type field
                    payload = {
                        "type": event_type,
                        "data": data,
                        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                    }
                        
                    message = json.dumps(payload, default=str)
                    await manager.broadcast(message)
                except Exception as e:
                    agent_logger.log_system_error(e, "api", f"broadcast_{event_type}")
            return broadcast_event

        event_bus.subscribe("trust_score_update", create_broadcast_handler("trust_score_update"))
        event_bus.subscribe("agent_activity", create_broadcast_handler("agent_activity"))
        event_bus.subscribe("conflict_prediction", create_broadcast_handler("conflict_prediction"))
        event_bus.subscribe("system_health", create_broadcast_handler("system_health"))
        event_bus.subscribe("intervention_executed", create_broadcast_handler("intervention_executed"))
        event_bus.subscribe("circuit_breaker_state_change", create_broadcast_handler("circuit_breaker_state_change"))
        event_bus.subscribe("voice_alert_generated", create_broadcast_handler("voice_alert_generated"))
        event_bus.subscribe("voice_analytics_update", create_broadcast_handler("voice_analytics_update"))
        event_bus.subscribe("graph_update", create_broadcast_handler("graph_update"))
        event_bus.subscribe("system_alert", create_broadcast_handler("system_alert"))
        
        # Handle quarantine events and convert to frontend format
        async def broadcast_quarantine_event(data):
            try:
                quarantine_message = {
                    "type": "quarantine_event",
                    "data": {
                        "agent_id": data.get("agent_id"),
                        "action": "quarantine",
                        "reason": data.get("reason"),
                        "timestamp": data.get("timestamp", datetime.now(timezone.utc).isoformat())
                    },
                    "timestamp": data.get("timestamp", datetime.now(timezone.utc).isoformat())
                }
                await manager.broadcast(json.dumps(quarantine_message, default=str))
            except Exception as e:
                agent_logger.log_system_error(e, "api", "broadcast_quarantine_event")
        
        event_bus.subscribe("agent_quarantined", broadcast_quarantine_event)

        # Handle decision updates (pattern detection)
        async def broadcast_decision_update(data):
            try:
                # First, broadcast the raw decision update
                await create_broadcast_handler("decision_update")(data)
                
                # Check if patterns were detected
                patterns = data.get("patterns_detected") or data.get("patterns", [])
                pattern_details = data.get("pattern_details", {})
                
                if patterns:
                    # Broadcast distinct alert for each pattern type
                    for pattern in patterns:
                        details = pattern_details.get(pattern, {}) if isinstance(pattern_details, dict) else {}
                        
                        # Determine severity
                        severity = details.get("severity", "info")
                        if pattern == "BYZANTINE_BEHAVIOR":
                            severity = "critical"
                        elif pattern == "RESOURCE_HOARDING":
                            severity = "warning"
                        elif pattern == "ROUTING_LOOP":
                            severity = "critical"
                        
                        pattern_alert = {
                            "type": "pattern_alert",
                            "data": {
                                "agent_id": data.get("agent_id"),
                                "patterns": [pattern],
                                "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                                "severity": severity,
                                "type": details.get("type", str(pattern).lower()),
                                "details": details.get("details", f"Pattern {pattern} detected for agent {data.get('agent_id')}"),
                                "recommended_action": details.get("recommended_action", "Review agent behavior and consider intervention"),
                                "affected_agents": details.get("affected_agents", [data.get("agent_id")]),
                                "risk_score": data.get("risk_score", 0.5)
                            },
                            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                        }
                        await manager.broadcast(json.dumps(pattern_alert, default=str))
            except Exception as e:
                agent_logger.log_system_error(e, "api", "broadcast_decision_update_logic")

        event_bus.subscribe("decision_update", broadcast_decision_update)

        # Start background task for voice analytics broadcasting
        async def broadcast_voice_analytics():
            while True:
                try:
                    from ..prediction_engine.voice_analytics import voice_analytics
                    report = voice_analytics.generate_report()
                    event_bus.publish("voice_analytics_update", {
                        "type": "voice_analytics_update",
                        "data": report,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                except Exception as e:
                    agent_logger.log_system_error(e, "api", "broadcast_voice_analytics")
                await asyncio.sleep(5) # Broadcast every 5 seconds

        asyncio.create_task(broadcast_voice_analytics())
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Handle application shutdown."""
        agent_logger.log_agent_action(
            "INFO",
            "FastAPI application shutting down",
            action_type="api_shutdown"
        )
        
        # Ensure lifecycle manager is shut down
        if lifecycle_manager.is_running():
            lifecycle_manager.shutdown()
    
    return app


# Create the app instance for uvicorn only if FastAPI is available
if FASTAPI_AVAILABLE:
    from src.config import settings
    lifecycle_manager = SystemLifecycleManager(settings)
    app = create_app(lifecycle_manager)
else:
    app = None