"""
Property-based tests for dashboard real-time updates.

**Feature: observability-trust-layer, Property 6: Dashboard real-time updates**
**Validates: Requirements 3.2, 3.3, 3.4**
"""
import pytest
import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from hypothesis import given, strategies as st, settings
from hypothesis.strategies import composite

from src.api.main import create_app, ConnectionManager
from src.system_lifecycle import SystemLifecycleManager
from src.event_bus import event_bus

# Custom async test runner for Hypothesis
def async_test(test_func):
    """Decorator to run async tests with Hypothesis."""
    def wrapper(*args, **kwargs):
        return asyncio.run(test_func(*args, **kwargs))
    return wrapper


@composite
def trust_score_update_data(draw):
    """Generate valid trust score update data."""
    agent_id = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc'))))
    old_score = draw(st.floats(min_value=0.0, max_value=100.0))
    new_score = draw(st.floats(min_value=0.0, max_value=100.0))
    timestamp = draw(st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 12, 31)))
    
    return {
        "type": "trust_score_update",
        "agent_id": agent_id,
        "old_score": old_score,
        "new_score": new_score,
        "timestamp": timestamp.isoformat() + "Z",
        "reason": "test_update"
    }


@composite
def system_health_data(draw):
    """Generate valid system health data."""
    overall_status = draw(st.sampled_from(["healthy", "degraded", "unhealthy"]))
    uptime = draw(st.floats(min_value=0.0, max_value=86400.0))  # Up to 24 hours
    
    component_names = ["redis", "datadog", "gemini", "circuit_breaker"]
    component_statuses = {}
    for name in component_names:
        status = draw(st.sampled_from(["healthy", "unhealthy", "degraded"]))
        component_statuses[name] = status
    
    return {
        "type": "system_health",
        "data": {
            "overall_status": overall_status,
            "uptime": uptime,
            "is_healthy": overall_status == "healthy",
            "component_statuses": component_statuses,
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }
    }


@composite
def quarantine_event_data(draw):
    """Generate valid quarantine event data."""
    agent_id = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc'))))
    action = draw(st.sampled_from(["quarantine", "release"]))
    reason = draw(st.text(min_size=1, max_size=100))
    
    return {
        "type": "quarantine_event",
        "agent_id": agent_id,
        "action": action,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    }


class TestDashboardRealTimeUpdates:
    """Test dashboard real-time update functionality."""
    
    def create_connection_manager(self):
        """Create a connection manager for testing."""
        return ConnectionManager()
    
    def create_mock_websocket(self):
        """Create a mock WebSocket connection."""
        websocket = AsyncMock()
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.send_json = AsyncMock()
        return websocket
    
    def create_lifecycle_manager(self):
        """Create a mock lifecycle manager."""
        manager = MagicMock(spec=SystemLifecycleManager)
        manager.get_status.return_value = {
            "state": "running",
            "uptime": 100.0,
            "start_time": datetime.utcnow().isoformat() + "Z",
            "is_healthy": True,
            "dependency_checks": 5,
            "health": {
                "overall_status": "healthy",
                "component_statuses": {
                    "redis": "healthy",
                    "datadog": "healthy",
                    "gemini": "healthy"
                }
            }
        }
        manager.is_running.return_value = True
        manager.is_healthy.return_value = True
        return manager
    
    @given(trust_score_update_data())
    @settings(max_examples=100)
    def test_trust_score_updates_broadcast_to_all_connections(self, update_data):
        """
        Property: For any trust score update, all connected WebSocket clients should receive the update.
        **Feature: observability-trust-layer, Property 6: Dashboard real-time updates**
        **Validates: Requirements 3.2, 3.3, 3.4**
        """
        @async_test
        async def run_test():
            connection_manager = self.create_connection_manager()
            
            # Connect multiple mock websockets
            websockets = [AsyncMock() for _ in range(3)]
            for ws in websockets:
                ws.accept = AsyncMock()
                ws.send_text = AsyncMock()
                ws.send_json = AsyncMock()
                await connection_manager.connect(ws)
            
            # Broadcast the update
            message = json.dumps(update_data, default=str)
            await connection_manager.broadcast(message)
            
            # Verify all connections received the message
            for ws in websockets:
                ws.send_text.assert_called_once_with(message)
        
        run_test()
    
    @given(system_health_data())
    @settings(max_examples=100)
    def test_system_health_updates_broadcast_immediately(self, health_data):
        """
        Property: For any system health change, dashboard should receive updates immediately.
        **Feature: observability-trust-layer, Property 6: Dashboard real-time updates**
        **Validates: Requirements 3.2, 3.3, 3.4**
        """
        @async_test
        async def run_test():
            connection_manager = self.create_connection_manager()
            mock_websocket = self.create_mock_websocket()
            
            # Connect websocket
            await connection_manager.connect(mock_websocket)
            
            # Broadcast health update
            message = json.dumps(health_data, default=str)
            await connection_manager.broadcast(message)
            
            # Verify websocket received the health update
            mock_websocket.send_text.assert_called_once_with(message)
            
            # Verify the message contains required health information
            parsed_data = json.loads(message)
            assert parsed_data["type"] == "system_health"
            assert "data" in parsed_data
            assert "overall_status" in parsed_data["data"]
            assert "component_statuses" in parsed_data["data"]
        
        run_test()
    
    @given(quarantine_event_data())
    @settings(max_examples=100)
    def test_quarantine_events_trigger_dashboard_updates(self, quarantine_data):
        """
        Property: For any quarantine event, dashboard should receive immediate notification.
        **Feature: observability-trust-layer, Property 6: Dashboard real-time updates**
        **Validates: Requirements 3.2, 3.3, 3.4**
        """
        @async_test
        async def run_test():
            connection_manager = self.create_connection_manager()
            mock_websocket = self.create_mock_websocket()
            
            # Connect websocket
            await connection_manager.connect(mock_websocket)
            
            # Broadcast quarantine event
            message = json.dumps(quarantine_data, default=str)
            await connection_manager.broadcast(message)
            
            # Verify websocket received the quarantine event
            mock_websocket.send_text.assert_called_once_with(message)
            
            # Verify the message contains required quarantine information
            parsed_data = json.loads(message)
            assert parsed_data["type"] == "quarantine_event"
            assert "agent_id" in parsed_data
            assert "action" in parsed_data
            assert parsed_data["action"] in ["quarantine", "release"]
        
        run_test()
    
    @given(st.lists(trust_score_update_data(), min_size=1, max_size=10))
    @settings(max_examples=50)
    def test_multiple_updates_maintain_order(self, updates_list):
        """
        Property: For any sequence of updates, dashboard should receive them in the same order.
        **Feature: observability-trust-layer, Property 6: Dashboard real-time updates**
        **Validates: Requirements 3.2, 3.3, 3.4**
        """
        @async_test
        async def run_test():
            connection_manager = self.create_connection_manager()
            mock_websocket = self.create_mock_websocket()
            
            # Connect websocket
            await connection_manager.connect(mock_websocket)
            
            # Send updates in sequence
            sent_messages = []
            for update in updates_list:
                message = json.dumps(update, default=str)
                sent_messages.append(message)
                await connection_manager.broadcast(message)
            
            # Verify all messages were sent in order
            assert mock_websocket.send_text.call_count == len(updates_list)
            
            # Verify call order matches sent order
            call_args = [call[0][0] for call in mock_websocket.send_text.call_args_list]
            assert call_args == sent_messages
        
        run_test()
    
    @given(trust_score_update_data())
    @settings(max_examples=100)
    def test_connection_failure_does_not_affect_other_connections(self, update_data):
        """
        Property: For any connection failure, other connections should continue receiving updates.
        **Feature: observability-trust-layer, Property 6: Dashboard real-time updates**
        **Validates: Requirements 3.2, 3.3, 3.4**
        """
        @async_test
        async def run_test():
            connection_manager = self.create_connection_manager()
            
            # Create working and failing websockets
            working_ws = AsyncMock()
            working_ws.accept = AsyncMock()
            working_ws.send_text = AsyncMock()
            
            failing_ws = AsyncMock()
            failing_ws.accept = AsyncMock()
            failing_ws.send_text = AsyncMock(side_effect=Exception("Connection failed"))
            
            # Connect both
            await connection_manager.connect(working_ws)
            await connection_manager.connect(failing_ws)
            
            # Broadcast update
            message = json.dumps(update_data, default=str)
            await connection_manager.broadcast(message)
            
            # Verify working connection still received the message
            working_ws.send_text.assert_called_once_with(message)
            # Verify failing connection was attempted
            failing_ws.send_text.assert_called_once_with(message)
        
        run_test()
    
    @given(st.integers(min_value=0, max_value=100))
    @settings(max_examples=50)
    def test_websocket_connection_management(self, num_connections):
        """
        Property: For any number of connections, connection manager should handle them correctly.
        **Feature: observability-trust-layer, Property 6: Dashboard real-time updates**
        **Validates: Requirements 3.2, 3.3, 3.4**
        """
        @async_test
        async def run_test():
            connection_manager = self.create_connection_manager()
            
            # Create and connect websockets
            websockets = []
            for _ in range(num_connections):
                ws = AsyncMock()
                ws.accept = AsyncMock()
                ws.send_text = AsyncMock()
                websockets.append(ws)
                await connection_manager.connect(ws)
            
            # Verify all connections are tracked
            assert len(connection_manager.active_connections) == num_connections
            
            # Disconnect half of them
            disconnect_count = num_connections // 2
            for i in range(disconnect_count):
                connection_manager.disconnect(websockets[i])
            
            # Verify remaining connections
            expected_remaining = num_connections - disconnect_count
            assert len(connection_manager.active_connections) == expected_remaining
        
        run_test()