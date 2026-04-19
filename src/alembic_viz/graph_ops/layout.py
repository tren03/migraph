"""Ordering and layout helpers for migration graphs."""

from collections import deque
from typing import Dict, List

from alembic_viz.graph_ops.validation import (
    _all_incoming_revisions,
    _node_map,
    detect_cycles,
)
from alembic_viz.models import GraphState


def _graph_edges(graph: GraphState) -> tuple[Dict[str, List[str]], Dict[str, int]]:
    revisions = set(_node_map(graph))
    adjacency = {revision: [] for revision in revisions}
    in_degree = {revision: 0 for revision in revisions}

    for migration in graph.migrations:
        for parent in _all_incoming_revisions(migration):
            if parent in revisions:
                adjacency[parent].append(migration.revision)
                in_degree[migration.revision] += 1

    for children in adjacency.values():
        children.sort()

    return adjacency, in_degree


def topological_sort(graph: GraphState) -> List[str]:
    """Return a stable topological ordering of revisions."""
    cycles = detect_cycles(graph)
    if cycles:
        raise ValueError(
            f"Cannot topologically sort cyclic graph: {' -> '.join(cycles[0])}"
        )

    adjacency, in_degree = _graph_edges(graph)
    queue = deque(
        sorted(revision for revision, degree in in_degree.items() if degree == 0)
    )
    ordered: List[str] = []

    while queue:
        revision = queue.popleft()
        ordered.append(revision)

        for child in adjacency[revision]:
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

        queue = deque(sorted(queue))

    return ordered


def calculate_layers(graph: GraphState) -> Dict[str, int]:
    """Assign each revision to a layer based on its deepest ancestor."""
    layers: Dict[str, int] = {}
    node_map = _node_map(graph)

    for revision in topological_sort(graph):
        parents = [
            parent
            for parent in _all_incoming_revisions(node_map[revision])
            if parent in node_map
        ]
        if not parents:
            layers[revision] = 0
            continue

        layers[revision] = max(layers[parent] for parent in parents) + 1

    return layers
