"""
Canonical graph schema layer. This is the single source of truth for nodes
and edges across the entire pipeline (mapper, reroute, orchestrator,
graph_utils). No other module should define its own Node/Edge type.
"""

from pydantic import BaseModel, Field


class Node(BaseModel):
    """One supply chain node. Canonical representation used everywhere."""

    id: str
    name: str
    type: str  # e.g. "supplier", "factory", "port", "warehouse", "distributor"
    region: str
    metadata: dict = Field(default_factory=dict)  # open slot for extra attributes


class Edge(BaseModel):
    """One directed connection between two nodes. Canonical representation used everywhere."""

    source: str  # Node.id
    target: str  # Node.id
    metadata: dict = Field(default_factory=dict)  # e.g. {"transport_mode": "ship"}


class Graph(BaseModel):
    """Container for a full supply chain graph."""

    nodes: list[Node]
    edges: list[Edge]