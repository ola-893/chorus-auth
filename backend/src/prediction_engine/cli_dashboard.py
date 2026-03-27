"""
CLI Dashboard for real-time monitoring of agent conflict prediction system.

Provides a command-line interface for observing agent behaviors, system status,
and intervention actions without requiring user input.
"""
import os
import sys
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .system_integration import conflict_predictor_system
from .models.core import ConflictAnalysis, QuarantineResult, InterventionAction
from .gemini_client import GeminiClient
from ..config import settings
from ..integrations.kafka_client import kafka_bus

logger = logging.getLogger(__name__)


@dataclass
class DashboardMetrics:
    """Container for dashboard display metrics."""
    timestamp: datetime
    total_agents: int
    active_agents: int
    quarantined_agents: int
    system_running: bool
    recent_conflicts: List[ConflictAnalysis]
    recent_interventions: List[InterventionAction]
    resource_utilization: Dict[str, float]
    trust_scores: Dict[str, int]
    current_risk_score: Optional[float]
    gemini_api_status: bool
    av_messages: List[Dict[str, Any]]


class CLIDashboard:
    """
    Real-time CLI dashboard for monitoring the agent conflict prediction system.
    
    Displays agent status, system metrics, conflict predictions, and intervention
    actions in a continuously updating terminal interface.
    """
    
    def __init__(self):
        """Initialize the CLI dashboard."""
        self.is_running = False
        self.display_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.refresh_interval = 2.0  # Seconds between updates
        self.max_display_items = 10  # Maximum items to show in lists
        
        # Display state
        self.current_metrics: Optional[DashboardMetrics] = None
        self.display_width = 80  # Terminal width
        self.display_height = 40  # Increased height for AgentVerse section
        
        # Conflict prediction components
        self.gemini_client: Optional[GeminiClient] = None
        self.conflict_history: List[ConflictAnalysis] = []
        self.last_prediction_time: Optional[datetime] = None
        
        # AgentVerse Visualization
        self.av_messages: List[Dict[str, Any]] = []
        self.av_consumer = None
        
        # Initialize Gemini client if API key is available
        try:
            if settings.gemini.api_key:
                self.gemini_client = GeminiClient()
                logger.info("Gemini client initialized for conflict prediction")
            else:
                logger.warning("Gemini API key not available - conflict prediction disabled")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            self.gemini_client = None
        
        logger.info("CLI Dashboard initialized")
    
    def start(self) -> None:
        """Start the real-time dashboard display."""
        if self.is_running:
            logger.warning("Dashboard is already running")
            return
        
        self.is_running = True
        self.stop_event.clear()
        
        # Initialize Kafka consumer for AgentVerse
        if settings.kafka.enabled:
            try:
                self.av_consumer = kafka_bus.create_temporary_consumer(group_id="cli-dashboard-av")
                if self.av_consumer:
                    self.av_consumer.subscribe([settings.kafka.agent_messages_topic])
            except Exception as e:
                logger.error(f"Failed to init AgentVerse consumer: {e}")

        # Clear screen and hide cursor
        self._clear_screen()
        self._hide_cursor()
        
        # Start display thread
        self.display_thread = threading.Thread(target=self._display_loop, daemon=True)
        self.display_thread.start()
        
        logger.info("CLI Dashboard started")
    
    def stop(self) -> None:
        """Stop the dashboard display."""
        if not self.is_running:
            return
        
        self.is_running = False
        self.stop_event.set()
        
        # Close consumer
        if self.av_consumer:
            try:
                self.av_consumer.close()
            except:
                pass

        # Wait for display thread to finish
        if self.display_thread and self.display_thread.is_alive():
            self.display_thread.join(timeout=3.0)
        
        # Show cursor and clear screen
        self._show_cursor()
        self._clear_screen()
        
        logger.info("CLI Dashboard stopped")
    
    def _display_loop(self) -> None:
        """Main display loop that continuously updates the dashboard."""
        while self.is_running and not self.stop_event.is_set():
            try:
                # Collect current metrics
                self.current_metrics = self._collect_metrics()
                
                # Update display
                self._update_display()
                
                # Wait for next update
                if self.stop_event.wait(self.refresh_interval):
                    break
                    
            except Exception as e:
                logger.exception(f"Error in dashboard display loop: {e}")
                # Continue running despite errors
                time.sleep(1.0)
    
    def _collect_metrics(self) -> DashboardMetrics:
        """Collect current system metrics for display."""
        try:
            # Poll AgentVerse Messages
            if self.av_consumer:
                # Poll a few times to drain buffer
                for _ in range(5):
                    msg = self.av_consumer.poll(timeout=0.1)
                    if msg is None:
                        break
                    if msg.error():
                        continue
                    
                    try:
                        import json
                        val = json.loads(msg.value().decode('utf-8'))
                        self.av_messages.append({
                            "timestamp": datetime.now(),
                            "sender": val.get("sender_id", "Unknown"),
                            "content": val.get("content", {}),
                            "type": val.get("message_type", "msg")
                        })
                        # Keep last 10
                        if len(self.av_messages) > 10:
                            self.av_messages = self.av_messages[-10:]
                    except Exception:
                        pass

            # Get system status
            system_status = conflict_predictor_system.get_system_status()
            
            # Get agent network information
            agent_network = conflict_predictor_system.agent_network
            active_agents = agent_network.get_active_agents() if agent_network else []
            
            # Get trust scores for active agents
            trust_scores = {}
            if active_agents:
                for agent in active_agents:
                    try:
                        score = conflict_predictor_system.trust_manager.get_trust_score(agent.agent_id)
                        trust_scores[agent.agent_id] = score
                    except Exception:
                        trust_scores[agent.agent_id] = 0
            
            # Get resource utilization
            resource_utilization = {}
            if agent_network and agent_network.resource_manager:
                from .models.core import ResourceType
                for resource_type in ResourceType:
                    try:
                        status = agent_network.resource_manager.get_resource_status(resource_type.value)
                        utilization = status.current_usage / max(status.total_capacity, 1)
                        resource_utilization[resource_type.value] = utilization
                    except Exception:
                        resource_utilization[resource_type.value] = 0.0
            
            # Get recent intervention history
            recent_interventions = []
            try:
                intervention_history = conflict_predictor_system.intervention_engine.get_intervention_history()
                # Get interventions from last 5 minutes
                cutoff_time = datetime.now() - timedelta(minutes=5)
                recent_interventions = [
                    action for action in intervention_history 
                    if action.timestamp > cutoff_time
                ][-self.max_display_items:]
            except Exception:
                pass
            
            # Perform conflict prediction if Gemini client is available
            current_risk_score = None
            gemini_api_status = False
            
            if self.gemini_client and active_agents:
                try:
                    # Test Gemini API status
                    gemini_api_status = self.gemini_client.test_connection()
                    
                    # Get current agent intentions
                    all_intentions = agent_network.get_all_intentions() if agent_network else []
                    
                    # Perform conflict analysis if we have intentions and enough time has passed
                    if (all_intentions and 
                        (not self.last_prediction_time or 
                         datetime.now() - self.last_prediction_time > timedelta(seconds=10))):
                        
                        try:
                            conflict_analysis = self.gemini_client.analyze_conflict_risk(all_intentions)
                            current_risk_score = conflict_analysis.risk_score
                            
                            # Add to conflict history
                            self.conflict_history.append(conflict_analysis)
                            # Keep only recent history (last 20 predictions)
                            if len(self.conflict_history) > 20:
                                self.conflict_history = self.conflict_history[-20:]
                            
                            self.last_prediction_time = datetime.now()
                            
                            # Process through intervention engine if risk is high
                            if conflict_analysis.risk_score > settings.conflict_prediction.risk_threshold:
                                result = conflict_predictor_system.intervention_engine.process_conflict_analysis(conflict_analysis)
                                if result and result.success:
                                    logger.info(f"High risk detected - quarantined agent {result.agent_id}")
                            
                        except Exception as e:
                            logger.error(f"Error during conflict prediction: {e}")
                            
                except Exception as e:
                    logger.error(f"Error testing Gemini API: {e}")
            
            # Get recent conflicts from history
            recent_conflicts = []
            if self.conflict_history:
                cutoff_time = datetime.now() - timedelta(minutes=5)
                recent_conflicts = [
                    conflict for conflict in self.conflict_history 
                    if conflict.timestamp > cutoff_time
                ][-self.max_display_items:]
            
            return DashboardMetrics(
                timestamp=datetime.now(),
                total_agents=system_status.get("total_agents", 0),
                active_agents=system_status.get("active_agents", 0),
                quarantined_agents=system_status.get("quarantined_agents", 0),
                system_running=system_status.get("system_running", False),
                recent_conflicts=recent_conflicts,
                recent_interventions=recent_interventions,
                resource_utilization=resource_utilization,
                trust_scores=trust_scores,
                current_risk_score=current_risk_score,
                gemini_api_status=gemini_api_status,
                av_messages=self.av_messages
            )
            
        except Exception as e:
            logger.error(f"Error collecting dashboard metrics: {e}")
            # Return empty metrics on error
            return DashboardMetrics(
                timestamp=datetime.now(),
                total_agents=0,
                active_agents=0,
                quarantined_agents=0,
                system_running=False,
                recent_conflicts=[],
                recent_interventions=[],
                resource_utilization={},
                trust_scores={},
                current_risk_score=None,
                gemini_api_status=False,
                av_messages=[]
            )
    
    def _update_display(self) -> None:
        """Update the terminal display with current metrics."""
        if not self.current_metrics:
            return
        
        # Move cursor to top-left
        sys.stdout.write("\033[H")
        
        # Build display content
        content = self._build_display_content()
        
        # Write content to terminal
        sys.stdout.write(content)
        sys.stdout.flush()
    
    def _build_display_content(self) -> str:
        """Build the complete dashboard display content."""
        if not self.current_metrics:
            return "No metrics available\n"
        
        lines = []
        
        # Header
        lines.append(self._build_header())
        lines.append("=" * self.display_width)
        
        # System status section
        lines.extend(self._build_system_status())
        lines.append("-" * self.display_width)
        
        # Agent status section
        lines.extend(self._build_agent_status())
        lines.append("-" * self.display_width)
        
        # Resource utilization section
        lines.extend(self._build_resource_status())
        lines.append("-" * self.display_width)
        
        # Conflict prediction section
        lines.extend(self._build_conflict_prediction_status())
        lines.append("-" * self.display_width)
        
        # Recent interventions section
        lines.extend(self._build_interventions_status())
        lines.append("-" * self.display_width)

        # AgentVerse section
        lines.extend(self._build_agentverse_status())
        
        # Pad to fill screen and clear any remaining content
        while len(lines) < self.display_height:
            lines.append(" " * self.display_width)
        
        return "\n".join(lines[:self.display_height])

    def _build_agentverse_status(self) -> List[str]:
        """Build the AgentVerse message stream section."""
        lines = ["AGENTVERSE TRAFFIC (Live):"]
        
        if not self.current_metrics.av_messages:
            lines.append("  No recent messages (Waiting for traffic...)")
            return lines
            
        for msg in self.current_metrics.av_messages:
            ts = msg["timestamp"].strftime("%H:%M:%S")
            sender = msg["sender"]
            # Truncate sender if too long
            if len(sender) > 15:
                sender = sender[:12] + "..."
            
            content = str(msg["content"])
            if len(content) > 40:
                content = content[:37] + "..."
            
            lines.append(f"  {ts} [{sender}] -> {content}")
            
        return lines
    
    def _build_header(self) -> str:
        """Build the dashboard header."""
        title = "CHORUS AGENT CONFLICT PREDICTOR - DASHBOARD"
        timestamp = self.current_metrics.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        # Center title
        title_padding = (self.display_width - len(title)) // 2
        title_line = " " * title_padding + title
        
        # Right-align timestamp
        timestamp_line = f"Last Update: {timestamp}".rjust(self.display_width)
        
        return f"{title_line}\n{timestamp_line}"
    
    def _build_system_status(self) -> List[str]:
        """Build the system status section."""
        lines = ["SYSTEM STATUS:"]
        
        status_indicator = "🟢 RUNNING" if self.current_metrics.system_running else "🔴 STOPPED"
        lines.append(f"  Status: {status_indicator}")
        
        # Gemini API status
        api_status = "🟢 CONNECTED" if self.current_metrics.gemini_api_status else "🔴 DISCONNECTED"
        lines.append(f"  Gemini API: {api_status}")
        
        lines.append(f"  Conflict Risk Threshold: {settings.conflict_prediction.risk_threshold}")
        lines.append(f"  Trust Score Threshold: {settings.trust_scoring.quarantine_threshold}")
        
        return lines
    
    def _build_agent_status(self) -> List[str]:
        """Build the agent status section."""
        lines = ["AGENT STATUS:"]
        
        lines.append(f"  Total Agents: {self.current_metrics.total_agents}")
        lines.append(f"  Active Agents: {self.current_metrics.active_agents}")
        lines.append(f"  Quarantined Agents: {self.current_metrics.quarantined_agents}")
        
        # Show trust scores for active agents
        if self.current_metrics.trust_scores:
            lines.append("  Trust Scores:")
            sorted_agents = sorted(
                self.current_metrics.trust_scores.items(),
                key=lambda x: x[1]  # Sort by trust score
            )
            
            for agent_id, trust_score in sorted_agents[:self.max_display_items]:
                status_icon = "⚠️" if trust_score < settings.trust_scoring.quarantine_threshold else "✅"
                lines.append(f"    {agent_id}: {trust_score:3d} {status_icon}")
        
        return lines
    
    def _build_resource_status(self) -> List[str]:
        """Build the resource utilization section."""
        lines = ["RESOURCE UTILIZATION:"]
        
        if not self.current_metrics.resource_utilization:
            lines.append("  No resource data available")
            return lines
        
        for resource_type, utilization in self.current_metrics.resource_utilization.items():
            percentage = utilization * 100
            
            # Create visual bar
            bar_width = 20
            filled_width = int(bar_width * utilization)
            bar = "█" * filled_width + "░" * (bar_width - filled_width)
            
            # Color coding
            if utilization > 0.8:
                status_icon = "🔴"
            elif utilization > 0.6:
                status_icon = "🟡"
            else:
                status_icon = "🟢"
            
            lines.append(f"  {resource_type:12s}: [{bar}] {percentage:5.1f}% {status_icon}")
        
        return lines
    
    def _build_conflict_prediction_status(self) -> List[str]:
        """Build the conflict prediction section."""
        lines = ["CONFLICT PREDICTION:"]
        
        # Current risk score
        if self.current_metrics.current_risk_score is not None:
            risk_score = self.current_metrics.current_risk_score
            percentage = risk_score * 100
            
            # Risk level indicator
            if risk_score > settings.conflict_prediction.risk_threshold:
                risk_level = "🔴 HIGH RISK"
            elif risk_score > 0.5:
                risk_level = "🟡 MODERATE"
            else:
                risk_level = "🟢 LOW RISK"
            
            # Create visual risk bar
            bar_width = 20
            filled_width = int(bar_width * risk_score)
            bar = "█" * filled_width + "░" * (bar_width - filled_width)
            
            lines.append(f"  Current Risk: [{bar}] {percentage:5.1f}% {risk_level}")
            
            # Last prediction time
            if self.last_prediction_time:
                time_ago = datetime.now() - self.last_prediction_time
                seconds_ago = int(time_ago.total_seconds())
                lines.append(f"  Last Update: {seconds_ago}s ago")
        else:
            if not self.current_metrics.gemini_api_status:
                lines.append("  Status: ⚠️  Gemini API unavailable")
            else:
                lines.append("  Status: ⏳ Waiting for agent data...")
        
        # Recent conflict predictions
        if self.current_metrics.recent_conflicts:
            lines.append("  Recent Predictions:")
            for conflict in self.current_metrics.recent_conflicts[-5:]:  # Show last 5
                timestamp = conflict.timestamp.strftime("%H:%M:%S")
                risk_pct = conflict.risk_score * 100
                
                # Risk indicator
                if conflict.risk_score > settings.conflict_prediction.risk_threshold:
                    indicator = "🔴"
                elif conflict.risk_score > 0.5:
                    indicator = "🟡"
                else:
                    indicator = "🟢"
                
                # Affected agents (truncate if too many)
                agents_str = ", ".join(conflict.affected_agents[:3])
                if len(conflict.affected_agents) > 3:
                    agents_str += f" (+{len(conflict.affected_agents) - 3} more)"
                
                lines.append(f"    {timestamp} {indicator} {risk_pct:5.1f}% - {agents_str}")
                
                # Show failure mode if high risk
                if conflict.risk_score > settings.conflict_prediction.risk_threshold:
                    failure_mode = conflict.predicted_failure_mode[:50] + "..." if len(conflict.predicted_failure_mode) > 50 else conflict.predicted_failure_mode
                    lines.append(f"      └─ {failure_mode}")
        
        return lines
    
    def _build_interventions_status(self) -> List[str]:
        """Build the recent interventions section."""
        lines = ["RECENT INTERVENTIONS:"]
        
        if not self.current_metrics.recent_interventions:
            lines.append("  No recent interventions")
            return lines
        
        # Show intervention statistics
        total_interventions = len(self.current_metrics.recent_interventions)
        quarantine_count = sum(1 for i in self.current_metrics.recent_interventions if i.action_type == "quarantine")
        lines.append(f"  Total: {total_interventions} | Quarantines: {quarantine_count}")
        lines.append("")
        
        # Show recent interventions with details
        for intervention in self.current_metrics.recent_interventions[-self.max_display_items:]:
            timestamp = intervention.timestamp.strftime("%H:%M:%S")
            action_type = intervention.action_type.upper()
            target = intervention.target_agent
            confidence = intervention.confidence * 100
            
            # Action type indicator
            if action_type == "QUARANTINE":
                action_icon = "🚫"
            else:
                action_icon = "⚡"
            
            lines.append(f"  {timestamp} {action_icon} {action_type:10s} {target:10s} ({confidence:3.0f}%)")
            
            # Show reason (truncated)
            reason = intervention.reason[:60] + "..." if len(intervention.reason) > 60 else intervention.reason
            lines.append(f"    └─ {reason}")
        
        return lines
    
    def _clear_screen(self) -> None:
        """Clear the terminal screen."""
        # ANSI escape sequence to clear screen
        sys.stdout.write("\033[2J")
        sys.stdout.flush()
    
    def _hide_cursor(self) -> None:
        """Hide the terminal cursor."""
        # ANSI escape sequence to hide cursor
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()
    
    def _show_cursor(self) -> None:
        """Show the terminal cursor."""
        # ANSI escape sequence to show cursor
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()


class DashboardManager:
    """
    Manager class for the CLI dashboard that provides a simple interface
    for starting and stopping the dashboard along with the system.
    """
    
    def __init__(self):
        """Initialize the dashboard manager."""
        self.dashboard = CLIDashboard()
        self.system_started = False
        
    def start_with_system(self, agent_count: Optional[int] = None) -> None:
        """
        Start both the conflict predictor system and the dashboard.
        
        Args:
            agent_count: Number of agents to create (optional)
        """
        try:
            logger.info("Starting system with dashboard...")
            
            # Start the conflict predictor system
            conflict_predictor_system.start_system(agent_count)
            self.system_started = True
            
            # Start the dashboard
            self.dashboard.start()
            
            logger.info("System and dashboard started successfully")
            
        except Exception as e:
            logger.exception(f"Error starting system with dashboard: {e}")
            self.stop()
            raise
    
    def stop(self) -> None:
        """Stop both the dashboard and the system."""
        try:
            logger.info("Stopping dashboard and system...")
            
            # Stop the dashboard first
            self.dashboard.stop()
            
            # Stop the system if it was started
            if self.system_started:
                conflict_predictor_system.stop_system()
                self.system_started = False
            
            logger.info("Dashboard and system stopped successfully")
            
        except Exception as e:
            logger.exception(f"Error stopping dashboard and system: {e}")
    
    def run_interactive(self, agent_count: Optional[int] = None) -> None:
        """
        Run the dashboard interactively until interrupted.
        
        Args:
            agent_count: Number of agents to create (optional)
        """
        try:
            self.start_with_system(agent_count)
            
            print("\nDashboard running... Press Ctrl+C to stop")
            
            # Keep running until interrupted
            while True:
                time.sleep(1.0)
                
        except KeyboardInterrupt:
            print("\nShutting down...")
        except Exception as e:
            logger.exception(f"Error in interactive dashboard: {e}")
        finally:
            self.stop()


# Global dashboard manager instance
dashboard_manager = DashboardManager()