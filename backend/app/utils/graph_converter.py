"""
Converts SQLAlchemy SupplyChain rows (Postgres) into the canonical in-memory
Graph (Node/Edge) used by the pipeline. This is the ONLY place that bridges
the DB schema's source_node_id/target_node_id columns to the pipeline's
Edge.source/Edge.target fields - no other module should do this conversion.
"""

from app.models.supply_chain import SupplyChain
from app.schemas.graph import Edge, Graph, Node


def supply_chain_to_graph(supply_chain: SupplyChain) -> Graph:
    nodes = [
        Node(
            id=str(n.id),
            name=n.name,
            type=n.type,
            region=n.region,
            metadata={"latitude": n.latitude, "longitude": n.longitude},
        )
        for n in supply_chain.nodes
    ]

    edges = [
        Edge(
            source=str(e.source_node_id),
            target=str(e.target_node_id),
            metadata={"transport_mode": e.transport_mode},
        )
        for e in supply_chain.edges
    ]

    return Graph(nodes=nodes, edges=edges)