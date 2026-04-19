"""Build the view model for the browser UI."""

from typing import Any, Dict, List

from alembic_viz.graph_ops import (
    calculate_layers,
    detect_cycles,
    detect_heads,
    detect_orphans,
    topological_sort,
)
from alembic_viz.models import GraphState

from alembic_viz.viewer.constants import (
    COLUMN_GAP,
    LAYER_GAP,
    NODE_HEIGHT,
    NODE_WIDTH,
    PADDING,
)


def build_view_model(graph: GraphState) -> Dict[str, Any]:
    """Build a browser-friendly graph payload with stable coordinates."""
    cycles = detect_cycles(graph)
    has_cycles = bool(cycles)
    order = (
        topological_sort(graph)
        if not has_cycles
        else [migration.revision for migration in graph.migrations]
    )
    layers = (
        calculate_layers(graph)
        if not has_cycles
        else {revision: 0 for revision in order}
    )
    heads = set(detect_heads(graph))
    orphans = set(detect_orphans(graph))
    cycle_nodes = {revision for cycle in cycles for revision in cycle[:-1]}

    # Group revisions by layer for column layout
    rows_by_layer: Dict[int, List[str]] = {}
    for revision in order:
        layer = layers.get(revision, 0)
        rows_by_layer.setdefault(layer, []).append(revision)

    # Calculate positions (invert layer for display: root at top)
    max_layer = max(rows_by_layer, default=0)
    positions: Dict[str, Dict[str, int]] = {}
    for layer, revisions in sorted(rows_by_layer.items()):
        display_layer = max_layer - layer
        for column, revision in enumerate(revisions):
            positions[revision] = {
                "x": PADDING + (column * COLUMN_GAP),
                "y": PADDING + (display_layer * LAYER_GAP),
            }

    # Override with saved UI positions
    for revision, position in graph.ui_state.positions.items():
        if revision in positions:
            positions[revision] = {"x": int(position.x), "y": int(position.y)}

    # Build nodes and edges
    nodes = []
    edges = []
    revision_set = {migration.revision for migration in graph.migrations}

    for migration in graph.migrations:
        position = positions[migration.revision]
        nodes.append(
            {
                "revision": migration.revision,
                "down_revision": migration.down_revision,
                "path": migration.path,
                "description": migration.metadata.description,
                "timestamp": str(migration.timestamp) if migration.timestamp else None,
                "x": position["x"],
                "y": position["y"],
                "is_head": migration.revision in heads,
                "is_orphan": migration.revision in orphans,
                "in_cycle": migration.revision in cycle_nodes,
            }
        )

        # Build edges from down_revision
        parents = migration.down_revision
        if isinstance(parents, str):
            parents = [parents]
        elif parents is None:
            parents = []

        for parent in parents:
            if parent in revision_set:
                edges.append({"from": parent, "to": migration.revision})

    # Calculate canvas size
    max_x = max((node["x"] for node in nodes), default=PADDING)
    max_y = max((node["y"] for node in nodes), default=PADDING)
    canvas = {
        "width": max_x + NODE_WIDTH + PADDING,
        "height": max_y + NODE_HEIGHT + PADDING,
    }

    return {
        "graph": graph.model_dump(mode="json"),
        "summary": {
            "migrations_count": len(graph.migrations),
            "heads": sorted(heads),
            "orphans": sorted(orphans),
            "cycles": cycles,
        },
        "layout": {
            "node_width": NODE_WIDTH,
            "node_height": NODE_HEIGHT,
            "canvas": canvas,
            "nodes": nodes,
            "edges": edges,
        },
    }


def preview_graph_state(graph: GraphState) -> Dict[str, Any]:
    """Return the viewer payload for an edited graph."""
    return build_view_model(graph)
