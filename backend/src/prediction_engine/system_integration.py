"""
System integration module for connecting all components of the agent conflict predictor.
"""
import logging
from typing import Optional

from src.prediction_engine.simulator import AgentNetwork
from src.prediction_engine.intervention_engine import intervention_engine
from src.prediction_engine.trust_manager import trust_manager
from src.prediction_engine.quarantine_manager import quarantine_manager
from src.prediction_engine.alert_classification import severity_classifier
from src.prediction_engine.alert_delivery_engine import alert_delivery_engine
from src.system_health import SystemHealthMonitor
from src.integrations.alerting_integration import AlertingIntegrationService
from src.logging_config import agent_logger
from ..config import settings
from ..logging_config import get_agent_logger
from ..system_health import health_monitor
from ..error_handling import system_recovery_context

logger = logging.getLogger(__name__)
agent_logger = get_agent_logger(__name__)


class ConflictPredictorSystem:
    """
    Main system class that integrates all components of the agent conflict predictor.
    
    Provides a unified interface for starting and managing the complete system
    including agent simulation, conflict prediction, and intervention capabilities.
    """
    
    def __init__(self):
        self.agent_network = AgentNetwork()
        self.system_running = False
        self.health_monitor = SystemHealthMonitor()
        self.alert_service = AlertingIntegrationService()
        
        # Initialize quarantine and intervention components
        from .quarantine_manager import RedisQuarantineManager
        from .intervention_engine import ConflictInterventionEngine
        self.quarantine_manager = RedisQuarantineManager()
        self.intervention_engine = ConflictInterventionEngine()
        
        agent_logger.log_agent_action(level='info', action_type='system_init', message='Conflict predictor system initialized')
    
    @system_recovery_context("system_integration", "start_system")
    def start_system(self, agent_count: int = 5):
        agent_logger.log_agent_action(level='info', action_type='system_startup', context={'agent_count': agent_count}, message='Starting conflict predictor system')
        self.agent_network = AgentNetwork(agent_count=agent_count)
        self.agent_network.create_agents()
        self.agent_network.start_simulation()

        self.health_monitor.start_monitoring()

        self.alert_service.start_monitoring()

        agent_logger.log_agent_action(level='info', action_type='system_started', context={'active_agents': len(self.agent_network.get_active_agents())}, message='Conflict predictor system started successfully')
        self.system_running = True
    
    def stop_system(self) -> None:
        """Stop the complete system."""
        with system_recovery_context(
            component="system_integration",
            operation="stop_system"
        ):
            agent_logger.log_agent_action(
                level="INFO",
                message="Stopping conflict predictor system",
                action_type="system_shutdown"
            )
            
            # Stop alerting monitoring
            import asyncio
            try:
                from ..integrations.alerting_integration import alerting_integration
                loop = asyncio.get_event_loop()
                loop.create_task(alerting_integration.stop_monitoring())
                logger.info("Alerting monitoring stopped")
            except Exception as e:
                logger.warning(f"Failed to stop alerting monitoring: {e}")
            
            # Stop Alert Delivery Engine
            alert_delivery_engine.stop()
            
            # Stop health monitoring
            health_monitor.stop_monitoring()
            
            # Stop agent simulation
            self.agent_network.stop_simulation()
            
            self.system_running = False
            agent_logger.log_agent_action(
                level="INFO",
                message="Conflict predictor system stopped successfully",
                action_type="system_stopped"
            )
    
    def _emergency_shutdown(self) -> None:
        """Emergency shutdown procedure for system recovery."""
        try:
            agent_logger.log_agent_action(
                "CRITICAL",
                "Executing emergency shutdown",
                action_type="emergency_shutdown"
            )
            
            # Stop health monitoring
            health_monitor.stop_monitoring()
            
            # Force stop agent simulation
            if hasattr(self, 'agent_network') and self.agent_network:
                self.agent_network.stop_simulation()
            
            agent_logger.log_agent_action(
                "INFO",
                "Emergency shutdown completed",
                action_type="emergency_shutdown_complete"
            )
            
        except Exception as e:
            agent_logger.log_system_error(
                e,
                component="system_integration",
                operation="emergency_shutdown"
            )
    
    def get_system_status(self) -> dict:
        """
        Get current system status.
        
        Returns:
            Dictionary with system status information
        """
        try:
            active_agents = self.agent_network.get_active_agents()
            quarantined_agents = self.quarantine_manager.get_quarantined_agents()
            
            return {
                "system_running": self.system_running,
                "total_agents": len(self.agent_network.agents),
                "active_agents": len(active_agents),
                "quarantined_agents": len(quarantined_agents),
                "quarantine_statistics": self.quarantine_manager.get_statistics(),
                "intervention_statistics": self.intervention_engine.get_statistics()
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {"error": str(e)}
    
    def simulate_conflict_scenario(self) -> None:
        """
        Simulate a conflict scenario for testing purposes.
        
        This method can be used to trigger conflicts and test the intervention system.
        """
        try:
            logger.info("Simulating conflict scenario...")
            
            # Get current agent intentions
            intentions = self.agent_network.get_all_intentions()
            
            if not intentions:
                logger.warning("No agent intentions available for conflict simulation")
                return
            
            # For demonstration, we can manually trigger a high-risk scenario
            # In a real system, this would come from the Gemini API analysis
            from .models.core import ConflictAnalysis
            from datetime import datetime
            
            # Create a mock high-risk conflict analysis
            mock_analysis = ConflictAnalysis(
                risk_score=0.85,  # Above threshold
                confidence_level=0.9,
                affected_agents=[intention.agent_id for intention in intentions[:3]],
                predicted_failure_mode="Resource contention leading to cascading failure",
                nash_equilibrium=None,
                timestamp=datetime.now()
            )
            
            # Process through intervention engine
            result = self.intervention_engine.process_conflict_analysis(mock_analysis)
            
            if result and result.success:
                logger.info(f"Conflict scenario processed: quarantined agent {result.agent_id}")
            else:
                logger.warning("Conflict scenario processing failed or no action taken")
                
        except Exception as e:
            logger.exception(f"Error simulating conflict scenario: {e}")


# Global system instance
conflict_predictor_system = ConflictPredictorSystem()