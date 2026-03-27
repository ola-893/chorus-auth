"""
Intervention engine for agent conflict prediction and quarantine management.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional

from .interfaces import InterventionEngine as InterventionEngineInterface, TrustManager, QuarantineManager
from .models.core import ConflictAnalysis, QuarantineResult, InterventionAction
from .trust_manager import trust_manager
from .quarantine_manager import quarantine_manager
from .alert_classification import severity_classifier
from .alert_delivery_engine import alert_delivery_engine
from ..config import settings
from ..logging_config import get_agent_logger
from ..integrations.datadog_client import datadog_client

logger = logging.getLogger(__name__)
agent_logger = get_agent_logger(__name__)


class ConflictInterventionEngine(InterventionEngineInterface):
    """
    Main intervention engine that evaluates conflicts and executes quarantine actions.
    
    Implements the core logic for determining when intervention is needed,
    identifying the most aggressive agents, and coordinating quarantine actions.
    """
    
    def __init__(self, trust_manager_instance: TrustManager = None, quarantine_manager_instance: QuarantineManager = None):
        """
        Initialize the intervention engine.
        
        Args:
            trust_manager_instance: Trust manager for score operations
            quarantine_manager_instance: Quarantine manager for isolation operations
        """
        self.trust_manager = trust_manager_instance or trust_manager
        self.quarantine_manager = quarantine_manager_instance or quarantine_manager
        self.conflict_risk_threshold = settings.conflict_prediction.risk_threshold
        self.intervention_history: List[InterventionAction] = []
        
        logger.info(f"Intervention engine initialized with risk threshold {self.conflict_risk_threshold}")
    
    def set_quarantine_manager(self, quarantine_manager_instance: QuarantineManager) -> None:
        """Set the quarantine manager instance."""
        self.quarantine_manager = quarantine_manager_instance
    
    def evaluate_intervention_need(self, conflict_analysis: ConflictAnalysis) -> bool:
        """
        Evaluate if intervention is needed based on conflict analysis.
        
        Args:
            conflict_analysis: Analysis results from Gemini API
            
        Returns:
            True if intervention is needed, False otherwise
        """
        try:
            # Check if risk score exceeds threshold
            needs_intervention = conflict_analysis.risk_score > self.conflict_risk_threshold
            
            if needs_intervention:
                agent_logger.log_agent_action(
                    "WARNING",
                    f"Intervention needed: risk score exceeds threshold",
                    action_type="intervention_needed",
                    risk_score=conflict_analysis.risk_score,
                    context={
                        "threshold": self.conflict_risk_threshold,
                        "affected_agents": conflict_analysis.affected_agents
                    }
                )
            else:
                logger.debug(
                    f"No intervention needed: risk score {conflict_analysis.risk_score:.3f} "
                    f"below threshold {self.conflict_risk_threshold}"
                )
            
            return needs_intervention
            
        except Exception as e:
            agent_logger.log_system_error(
                e,
                component="intervention_engine",
                operation="evaluate_intervention_need"
            )
            # Default to no intervention on error to prevent false positives
            return False
    
    def identify_most_aggressive_agent(self, agents: List[str]) -> str:
        """
        Identify the most aggressive agent from a list of agents.
        
        Uses a combination of trust score and recent behavior patterns
        to determine which agent is most likely causing conflicts.
        
        Args:
            agents: List of agent IDs to evaluate
            
        Returns:
            Agent ID of the most aggressive agent
            
        Raises:
            ValueError: If no agents provided or no valid agents found
        """
        if not agents:
            raise ValueError("No agents provided for evaluation")
        
        try:
            agent_scores = {}
            
            for agent_id in agents:
                # Get trust score (lower = more aggressive)
                trust_score = self.trust_manager.get_trust_score(agent_id)
                
                # Get quarantine history
                quarantine_count = 0
                try:
                    if hasattr(self.trust_manager, 'get_quarantine_count'):
                        quarantine_count = self.trust_manager.get_quarantine_count(agent_id)
                except Exception:
                    pass
                
                # Calculate aggression score (higher = more aggressive)
                # Lower trust score and higher quarantine count indicate more aggression
                aggression_score = (100 - trust_score) + (quarantine_count * 10)
                agent_scores[agent_id] = aggression_score
                
                logger.debug(
                    f"Agent {agent_id}: trust={trust_score}, quarantines={quarantine_count}, "
                    f"aggression={aggression_score}"
                )
            
            # Find agent with highest aggression score
            most_aggressive = max(agent_scores.keys(), key=lambda x: agent_scores[x])
            
            logger.info(
                f"Most aggressive agent identified: {most_aggressive} "
                f"(aggression score: {agent_scores[most_aggressive]})"
            )
            
            return most_aggressive
            
        except Exception as e:
            logger.error(f"Error identifying most aggressive agent: {e}")
            # Fallback to first agent if analysis fails
            return agents[0]
    
    def execute_quarantine(self, agent_id: str, reason: str) -> QuarantineResult:
        """
        Execute quarantine for a specific agent.
        
        Args:
            agent_id: Agent to quarantine
            reason: Reason for quarantine
            
        Returns:
            Result of quarantine operation
        """
        try:
            if not self.quarantine_manager:
                logger.error("No quarantine manager available")
                return QuarantineResult(
                    success=False,
                    agent_id=agent_id,
                    reason="No quarantine manager available",
                    timestamp=datetime.now()
                )
            
            # Execute quarantine through quarantine manager
            result = self.quarantine_manager.quarantine_agent(agent_id, reason)
            
            if result.success:
                # Update trust score for quarantined agent
                self.trust_manager.update_trust_score(
                    agent_id, 
                    -20,  # Quarantine penalty
                    f"Quarantined: {reason}"
                )
                
                # Record intervention action
                intervention = InterventionAction(
                    action_type="quarantine",
                    target_agent=agent_id,
                    reason=reason,
                    confidence=1.0,  # High confidence for executed actions
                    timestamp=datetime.now()
                )
                self.intervention_history.append(intervention)
                
                # Keep only recent history (last 100 interventions)
                if len(self.intervention_history) > 100:
                    self.intervention_history = self.intervention_history[-100:]
                
                agent_logger.log_quarantine_action(
                    agent_id=agent_id,
                    action="quarantine",
                    reason=reason,
                    success=True,
                    context={"intervention_id": len(self.intervention_history)}
                )
                
                # Emit intervention event
                try:
                    from ..event_bus import event_bus
                    event_bus.publish("intervention_executed", {
                        "type": "intervention_executed",
                        "action_type": "quarantine",
                        "agent_id": agent_id,
                        "reason": reason,
                        "success": True,
                        "intervention_id": len(self.intervention_history),
                        "timestamp": datetime.now().isoformat()
                    })
                except Exception as e:
                    logger.warning(f"Failed to emit intervention event: {e}")
                
                # Send observability data to Datadog
                try:
                    datadog_client.send_metric(
                        "chorus.intervention.quarantine_success",
                        1.0,
                        tags=[f"agent_id:{agent_id}"],
                        metric_type="count"
                    )
                    
                    datadog_client.send_log(
                        f"Agent {agent_id} quarantined successfully",
                        level="WARN",
                        context={
                            "agent_id": agent_id,
                            "reason": reason,
                            "intervention_id": len(self.intervention_history)
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to send quarantine success metrics to Datadog: {e}")
            else:
                agent_logger.log_quarantine_action(
                    agent_id=agent_id,
                    action="quarantine",
                    reason=reason,
                    success=False,
                    context={"failure_reason": result.reason}
                )
                
                # Emit intervention failure event
                try:
                    from ..event_bus import event_bus
                    event_bus.publish("intervention_executed", {
                        "type": "intervention_executed",
                        "action_type": "quarantine",
                        "agent_id": agent_id,
                        "reason": reason,
                        "success": False,
                        "failure_reason": result.reason,
                        "timestamp": datetime.now().isoformat()
                    })
                except Exception as e:
                    logger.warning(f"Failed to emit intervention failure event: {e}")
                
                # Send observability data to Datadog for failures
                try:
                    datadog_client.send_metric(
                        "chorus.intervention.quarantine_failure",
                        1.0,
                        tags=[f"agent_id:{agent_id}"],
                        metric_type="count"
                    )
                    
                    datadog_client.send_log(
                        f"Agent {agent_id} quarantine failed: {result.reason}",
                        level="ERROR",
                        context={
                            "agent_id": agent_id,
                            "reason": reason,
                            "failure_reason": result.reason
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to send quarantine failure metrics to Datadog: {e}")
            
            return result
            
        except Exception as e:
            agent_logger.log_system_error(
                e,
                component="intervention_engine",
                operation="execute_quarantine",
                agent_id=agent_id,
                context={"reason": reason}
            )
            return QuarantineResult(
                success=False,
                agent_id=agent_id,
                reason=f"Quarantine execution error: {str(e)}",
                timestamp=datetime.now()
            )
    
    def process_conflict_analysis(self, conflict_analysis: ConflictAnalysis) -> Optional[QuarantineResult]:
        """
        Process a conflict analysis and take appropriate intervention actions.
        
        Args:
            conflict_analysis: Analysis results from conflict prediction
            
        Returns:
            Quarantine result if intervention was taken, None otherwise
        """
        try:
            # Check if intervention is needed
            if not self.evaluate_intervention_need(conflict_analysis):
                return None
            
            # Identify most aggressive agent
            if not conflict_analysis.affected_agents:
                logger.warning("No affected agents in conflict analysis")
                return None
            
            most_aggressive = self.identify_most_aggressive_agent(conflict_analysis.affected_agents)
            
            # Classify and deliver alert
            alert = severity_classifier.classify_conflict(conflict_analysis)
            alert_delivery_engine.process_alert(alert)
            
            # Execute quarantine
            reason = f"High conflict risk ({conflict_analysis.risk_score:.3f}): {conflict_analysis.predicted_failure_mode}"
            result = self.execute_quarantine(most_aggressive, reason)
            
            return result
            
        except Exception as e:
            logger.exception(f"Error processing conflict analysis: {e}")
            return None
    
    def get_intervention_history(self) -> List[InterventionAction]:
        """
        Get the history of intervention actions.
        
        Returns:
            List of intervention actions
        """
        return self.intervention_history.copy()
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get intervention statistics.
        
        Returns:
            Dictionary with intervention statistics
        """
        total_interventions = len(self.intervention_history)
        quarantine_actions = sum(1 for action in self.intervention_history if action.action_type == "quarantine")
        
        return {
            "total_interventions": total_interventions,
            "quarantine_actions": quarantine_actions,
            "other_actions": total_interventions - quarantine_actions
        }


# Global intervention engine instance
intervention_engine = ConflictInterventionEngine()