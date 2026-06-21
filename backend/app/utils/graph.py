"""
Deterministic graph traversal utilities. No LLM involved - this is plain
Python graph logic (BFS), used by the Reroute Agent to find candidate
alternative nodes before asking the LLM to phrase a suggestion.

Operates exclusively on the canonical app.schemas.graph types (Node, Edge).
"""

from collections import deque

from app.schemas.graph import Edge, Node


def _build_adjacency(nodes: list[Node], edges: list[Edge]) -> dict[str, set[str]]:
    adjacency: dict[str, set[str]] = {n.id: set() for n in nodes}
    for edge in edges:
        if edge.source in adjacency and edge.target in adjacency:
            adjacency[edge.source].add(edge.target)
            adjacency[edge.target].add(edge.source)  # treat as undirected for alt-finding
    return adjacency


def _bfs_distances(start_id: str, adjacency: dict[str, set[str]]) -> dict[str, int]:
    distances = {start_id: 0}
    queue = deque([start_id])
    while queue:
        current = queue.popleft()
        for neighbor in adjacency.get(current, set()):
            if neighbor not in distances:
                distances[neighbor] = distances[current] + 1
                queue.append(neighbor)
    return distances


def find_alternative_nodes(
    impacted_node: Node,
    all_nodes: list[Node],
    edges: list[Edge],
    max_alternatives: int = 3,
) -> list[Node]:
    """
    Finds candidate alternative nodes for a disrupted node: other nodes of the
    same type, ranked by graph distance (BFS) from the impacted node (closer
    is preferred). Falls back to same-type nodes in declaration order if the
    graph is disconnected or has no path.
    """
    same_type_candidates = [
        n for n in all_nodes if n.type == impacted_node.type and n.id != impacted_node.id
    ]
    if not same_type_candidates:
        return []

    if not edges:
        return same_type_candidates[:max_alternatives]

    adjacency = _build_adjacency(all_nodes, edges)
    distances = _bfs_distances(impacted_node.id, adjacency)

    def sort_key(node: Node) -> tuple[float, str]:
        # Unreachable nodes sort last; ties broken by name for determinism.
        return (distances.get(node.id, float("inf")), node.name)

    ranked = sorted(same_type_candidates, key=sort_key)
    return ranked[:max_alternatives]