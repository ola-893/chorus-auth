"""
Data models for Causal Graph Engine.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime

@dataclass
class CausalEdge:
    source: str
    target: str
    weight: float = 1.0
    interaction_type: str = "communication"
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())

@dataclass
class GraphNode:
    id: str
    status: str = "active" # active, quarantined
    trust_score: int = 100
    last_updated: float = field(default_factory=lambda: datetime.now().timestamp())

@dataclass
class GraphMetrics:
    node_count: int
    edge_count: int
    density: float
    clustering_coefficient: float
    detected_loops: List[List[str]]
    quarantined_nodes: int
