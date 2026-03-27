"""
Advanced pattern detection engine for identifying complex emergent behaviors.
"""
from typing import List, Dict, Any, Set, Optional
from collections import defaultdict
from .models.core import AgentIntention
from ..mapper.models import GraphMetrics

class PatternDetector:
    """
    Detects complex patterns in agent behavior and interaction topology.
    """
    
    def __init__(self):
        """Initialize pattern detector with tracking state."""
        self.interaction_graph: Dict[str, Set[str]] = defaultdict(set)
        self.message_counts: Dict[str, int] = defaultdict(int)
    
    def record_interaction(self, source: str, target: str):
        """Record an interaction between agents for pattern detection."""
        self.interaction_graph[source].add(target)
        self.message_counts[source] += 1
    
    def detect_routing_loop(self, agent_id: str, path: Optional[List[str]] = None) -> Optional[List[str]]:
        """
        Detect routing loops in agent communication patterns.
        Returns the loop path if detected, None otherwise.
        """
        if path is None:
            path = [agent_id]
        
        # Check if we've seen this agent before in the path
        if agent_id in path[:-1]:
            # Found a loop - return the loop portion
            loop_start = path.index(agent_id)
            return path[loop_start:]
        
        # Explore neighbors
        for neighbor in self.interaction_graph.get(agent_id, set()):
            if neighbor in path:
                # Found a loop
                loop_start = path.index(neighbor)
                return path[loop_start:] + [neighbor]
            
            # Recursively check for loops (limit depth to prevent infinite recursion)
            if len(path) < 10:
                new_path = path + [neighbor]
                loop = self.detect_routing_loop(neighbor, new_path)
                if loop:
                    return loop
        
        return None
    
    def detect_resource_hoarding(self, agent_id: str, history: List[Dict]) -> bool:
        """
        Detect if an agent is hoarding resources.
        Criterion: High frequency of high-priority requests for same resource without release.
        """
        if not history:
            return False
            
        # Simplified logic: Check if last 5 requests are for high resources
        recent = history[-5:]
        if len(recent) < 5:
            return False
            
        # Check if we are analyzing Trust Adjustments or Agent Intentions
        if 'adjustment' in recent[0]:
            high_usage_count = sum(1 for h in recent if h.get('adjustment', 0) < -10) # Assuming negative adjustment implies consumption
        else:
            # Assume AgentIntention dicts
            # High usage = high requested amount (e.g., > 70% of some norm, say 70) or high priority
            high_usage_count = sum(1 for h in recent if h.get('requested_amount', 0) > 70 or h.get('priority_level', 0) >= 8)
            
        return high_usage_count >= 4

    def detect_communication_cascade(self, metrics: GraphMetrics) -> bool:
        """
        Detect if a communication cascade is occurring.
        Criterion: Sudden spike in edge count or density.
        """
        # In a real system, we'd compare against baseline.
        # Here we check if density is dangerously high for a sparse network
        return metrics.density > 0.8 and metrics.node_count > 5
    
    def detect_communication_cascade_by_agent(self, agent_id: str, time_window: int = 60) -> bool:
        """
        Detect if an agent is causing a communication cascade.
        Criterion: Abnormally high message rate.
        """
        # Check if agent has sent more than threshold messages
        # In a real system, this would be time-windowed
        return self.message_counts.get(agent_id, 0) > 50

    def detect_byzantine_behavior(self, agent_id: str, history: List[Dict]) -> bool:
        """
        Detect inconsistent/Byzantine behavior.
        Criterion: Alternating between cooperation (positive score) and conflict (negative score).
        """
        if len(history) < 4:
            return False
            
        # Check for sign flips in score adjustments
        flips = 0
        for i in range(1, len(history)):
            prev = history[i-1].get('adjustment', 0)
            curr = history[i].get('adjustment', 0)
            if (prev > 0 and curr < 0) or (prev < 0 and curr > 0):
                flips += 1
                
        # High volatility in behavior
        return flips >= 3
    
    def get_affected_agents_in_loop(self, loop: List[str]) -> List[str]:
        """Get all agents affected by a routing loop."""
        return list(set(loop))
    
    def clear_old_data(self):
        """Clear old tracking data to prevent memory buildup."""
        # Keep only recent interactions (last 1000 per agent)
        for agent_id in list(self.interaction_graph.keys()):
            if len(self.interaction_graph[agent_id]) > 1000:
                # Keep only most recent
                self.interaction_graph[agent_id] = set(list(self.interaction_graph[agent_id])[-1000:])
        
        # Reset message counts periodically
        if sum(self.message_counts.values()) > 10000:
            self.message_counts.clear()

# Global instance
pattern_detector = PatternDetector()
