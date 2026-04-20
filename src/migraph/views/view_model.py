"""View model builders for the HTTP server."""

from typing import Any, Dict, List

from migraph.domain.models import GraphState
from migraph.services.graph_service import GraphService


def build_view_model(
    graph: GraphState, graph_service: GraphService | None = None
) -> Dict[str, Any]:
    graph_service = graph_service or GraphService()

    cycles = graph_service.detect_cycles(graph)
    heads = set(graph_service.detect_heads(graph))
    orphans = set(graph_service.detect_orphans(graph))
    cycle_nodes = {revision for cycle in cycles for revision in cycle[:-1]}

    revision_set = {migration.revision for migration in graph.migrations}
    nodes = []
    edges = []

    for migration in graph.migrations:
        nodes.append({
            "revision": migration.revision,
            "down_revision": migration.down_revision,
            "path": migration.path,
            "description": migration.metadata.description,
            "timestamp": str(migration.timestamp) if migration.timestamp else None,
            "is_head": migration.revision in heads,
            "is_orphan": migration.revision in orphans,
            "in_cycle": migration.revision in cycle_nodes,
        })

        parents = migration.down_revision
        if isinstance(parents, str):
            parents = [parents]
        elif parents is None:
            parents = []

        for parent in parents:
            if parent in revision_set:
                edges.append({"source": parent, "target": migration.revision})

    return {
        "graph": graph.model_dump(mode="json"),
        "summary": {
            "migrations_count": len(graph.migrations),
            "heads": sorted(heads),
            "orphans": sorted(orphans),
            "cycles": cycles,
        },
        "nodes": nodes,
        "edges": edges,
    }


def preview_graph_state(graph: GraphState) -> Dict[str, Any]:
    return build_view_model(graph)
