"""
Graph Topology Manager for maintaining real-time causal graph.
"""
from typing import Dict, List, Set, Optional
import time
from dataclasses import asdict
import json

from .models import CausalEdge, GraphNode, GraphMetrics
from ..logging_config import get_agent_logger
from ..integrations.kafka_client import kafka_bus
from ..config import settings
from ..event_bus import event_bus

agent_logger = get_agent_logger(__name__)

try:
    import networkx as nx
except ImportError as e:
    agent_logger.error(f"Failed to import networkx: {e}")
    nx = None

class GraphTopologyManager:
    """
    Manages the real-time causal graph of agent interactions.
    """
    
    def __init__(self):
        self.graph = nx.DiGraph() if nx else None
        self.nodes: Dict[str, GraphNode] = {}
        self.update_topic = settings.kafka.causal_graph_updates_topic
        
        # Subscribe to quarantine events
        event_bus.subscribe("agent_quarantined", self._handle_quarantine_event)
        
    def _handle_quarantine_event(self, data: Dict):
        """Handle agent quarantine event."""
        agent_id = data.get("agent_id")
        if agent_id:
            self.update_node_status(agent_id, "quarantined", 0)
        
    def add_interaction(self, source: str, target: str, interaction_type: str = "communication"):
        """
        Add an interaction (edge) to the graph.
        """
        global nx
        if nx is None:
            try:
                import networkx as nx_new
                nx = nx_new
                self.graph = nx.DiGraph()
            except ImportError:
                # Use a simple mock to prevent noise and crashes
                class MockGraph:
                    def add_node(self, *args, **kwargs): pass
                    def add_edge(self, *args, **kwargs): pass
                    def has_edge(self, *args, **kwargs): return False
                    def number_of_nodes(self): return 0
                    def number_of_edges(self): return 0
                    def __getitem__(self, key): return {}
                    @property
                    def nodes(self): return {}
                self.graph = MockGraph()

        if self.graph is None:
            agent_logger.warning("Graph not initialized (NetworkX missing?)")
            return

        # Ensure nodes exist
        self._ensure_node(source)
        self._ensure_node(target)
        
        # Add or update edge
        timestamp = time.time()
        edge = CausalEdge(
            source=source, 
            target=target, 
            interaction_type=interaction_type,
            timestamp=timestamp
        )
        
        if self.graph.has_edge(source, target):
            # Update weight/timestamp
            self.graph[source][target]['weight'] += 1
            self.graph[source][target]['last_interaction'] = timestamp
        else:
            self.graph.add_edge(source, target, weight=1, last_interaction=timestamp, type=interaction_type)
            
        self._publish_update("edge_added", asdict(edge))
        
    def _ensure_node(self, agent_id: str):
        """Ensure node exists in graph and tracking."""
        if agent_id not in self.nodes:
            node = GraphNode(id=agent_id)
            self.nodes[agent_id] = node
            if self.graph:
                self.graph.add_node(agent_id, status=node.status)
            self._publish_update("node_added", asdict(node))

    def update_node_status(self, agent_id: str, status: str, trust_score: int):
        """Update node status (e.g. quarantine)."""
        self._ensure_node(agent_id)
        node = self.nodes[agent_id]
        node.status = status
        node.trust_score = trust_score
        node.last_updated = time.time()
        
        if self.graph:
            self.graph.nodes[agent_id]['status'] = status
            self.graph.nodes[agent_id]['trust_score'] = trust_score
            
        self._publish_update("node_updated", asdict(node))

    def detect_routing_loops(self) -> List[List[str]]:
        """
        Detect loops in the interaction graph.
        """
        if self.graph is None:
            return []
            
        try:
            # Detect simple cycles
            cycles = list(nx.simple_cycles(self.graph))
            return cycles
        except Exception as e:
            agent_logger.log_system_error(e, "topology_manager", "detect_loops")
            return []

    def get_metrics(self) -> GraphMetrics:
        """Calculate graph metrics."""
        if self.graph is None:
            return GraphMetrics(0, 0, 0.0, 0.0, [], 0)
            
        try:
            loops = self.detect_routing_loops()
            quarantined = sum(1 for n in self.nodes.values() if n.status == 'quarantined')
            
            # Basic metrics
            node_count = self.graph.number_of_nodes()
            edge_count = self.graph.number_of_edges()
            
            # Density
            density = nx.density(self.graph)
            
            # Clustering coefficient (average) - requires converting to undirected for simple definition 
            # or use simple approximation
            try:
                clustering = nx.average_clustering(self.graph)
            except:
                clustering = 0.0

            return GraphMetrics(
                node_count=node_count,
                edge_count=edge_count,
                density=density,
                clustering_coefficient=clustering,
                detected_loops=loops,
                quarantined_nodes=quarantined
            )
        except Exception as e:
            agent_logger.log_system_error(e, "topology_manager", "get_metrics")
            return GraphMetrics(0, 0, 0.0, 0.0, [], 0)

    def _publish_update(self, event_type: str, data: Dict):
        """Publish graph update to Kafka and EventBus."""
        payload = {
            "event_type": event_type,
            "data": data,
            "timestamp": time.time()
        }
        
        
        # Publish to Kafka
        kafka_bus.produce(
            self.update_topic,
            payload,
            key="graph_update"
        )
        
        # Publish to internal EventBus (for WebSocket)
        event_bus.publish("graph_update", payload)

# Global instance
topology_manager = GraphTopologyManager()
