"""View model builders for the HTTP server."""

from collections import deque
from typing import Any, Dict, List

from mviz.domain.models import GraphState
from mviz.services.graph_service import GraphService

# Layout constants
NODE_WIDTH = 220
NODE_HEIGHT = 72
LAYER_GAP = 130
COLUMN_GAP = 260
PADDING = 80


def build_view_model(
    graph: GraphState, graph_service: GraphService | None = None
) -> Dict[str, Any]:
    """Build a browser-friendly graph payload with coordinates."""
    graph_service = graph_service or GraphService()

    cycles = graph_service.detect_cycles(graph)
    has_cycles = bool(cycles)

    if has_cycles:
        order, layers = _calculate_cycle_tolerant_layout(graph)
    else:
        order = graph_service.topological_sort(graph)
        layers = graph_service.calculate_layers(graph)
    heads = set(graph_service.detect_heads(graph))
    orphans = set(graph_service.detect_orphans(graph))
    cycle_nodes = {revision for cycle in cycles for revision in cycle[:-1]}

    max_layer = max((layers.get(r, 0) for r in order), default=0)
    positions: Dict[str, Dict[str, int]] = {}

    if not has_cycles:
        node_lanes = _assign_lanes(order, graph)
        for revision in order:
            layer = layers.get(revision, 0)
            positions[revision] = {
                "x": PADDING + node_lanes[revision] * COLUMN_GAP,
                "y": PADDING + (max_layer - layer) * LAYER_GAP,
            }
    else:
        # Cycle-tolerant fallback: naive column assignment within each layer
        rows_by_layer: Dict[int, List[str]] = {}
        for revision in order:
            rows_by_layer.setdefault(layers.get(revision, 0), []).append(revision)
        for layer, revisions in sorted(rows_by_layer.items()):
            display_layer = max_layer - layer
            for column, revision in enumerate(revisions):
                positions[revision] = {
                    "x": PADDING + column * COLUMN_GAP,
                    "y": PADDING + display_layer * LAYER_GAP,
                }

    node_map = {migration.revision: migration for migration in graph.migrations}
    pinned_revisions = set(graph.ui_state.pinned)

    # Detached nodes: pinned + no parents. Place them in a dedicated zone
    # below the main graph to avoid overlapping with re-flowed nodes.
    detached_revisions = sorted(
        r for r in pinned_revisions
        if r in node_map and not _incoming_revisions(node_map[r])
    )

    # Apply pinned positions for non-detached pinned nodes (e.g., manually dragged)
    for revision, position in graph.ui_state.positions.items():
        if revision not in pinned_revisions or revision in detached_revisions:
            continue
        migration = node_map.get(revision)
        if migration is None or _incoming_revisions(migration):
            continue
        positions[revision] = {"x": int(position.x), "y": int(position.y)}

    # Place detached nodes in a row below the main graph
    if detached_revisions:
        non_detached_ys = [p["y"] for r, p in positions.items() if r not in detached_revisions]
        detached_y = (max(non_detached_ys, default=PADDING)) + NODE_HEIGHT + LAYER_GAP
        for col, revision in enumerate(detached_revisions):
            positions[revision] = {"x": PADDING + col * COLUMN_GAP, "y": detached_y}

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


def _assign_lanes(order: List[str], graph: GraphState) -> Dict[str, int]:
    """Assign each revision to a horizontal lane so branch nodes share a column.

    Processes nodes oldest-first. Each root starts a new lane. When a parent
    has multiple children, the child with the most descendants (primary/longest
    chain) inherits the parent's lane; secondary children get new lanes.
    Merge nodes (multiple parents) take the leftmost parent lane.
    """
    rev_set = {m.revision for m in graph.migrations}

    # forward_adj: parent → children (sorted for determinism)
    forward_adj: Dict[str, List[str]] = {r: [] for r in rev_set}
    for migration in graph.migrations:
        for parent in _incoming_revisions(migration):
            if parent in rev_set:
                forward_adj[parent].append(migration.revision)
    for children in forward_adj.values():
        children.sort()

    # reverse_adj: child → parents
    reverse_adj: Dict[str, List[str]] = {r: [] for r in rev_set}
    for migration in graph.migrations:
        for parent in _incoming_revisions(migration):
            if parent in rev_set:
                reverse_adj[migration.revision].append(parent)

    # Descendant count (leaf→root pass) to pick primary child per parent.
    # The child with the most descendants is on the "main" branch.
    desc_count: Dict[str, int] = {r: 0 for r in rev_set}
    for revision in reversed(order):
        desc_count[revision] = 1 + sum(
            desc_count[c] for c in forward_adj.get(revision, [])
        )

    def primary_first_children(revision: str) -> List[str]:
        return sorted(
            forward_adj.get(revision, []), key=lambda c: -desc_count[c]
        )

    lanes: Dict[str, int] = {}
    next_lane = 0

    for revision in order:
        if revision not in lanes:
            parents_assigned = [p for p in reverse_adj.get(revision, []) if p in lanes]
            if not parents_assigned:
                lanes[revision] = next_lane
                next_lane += 1
            else:
                # Merge: take leftmost parent lane
                lanes[revision] = min(lanes[p] for p in parents_assigned)

        # Pre-assign new lanes to secondary children so they don't inherit this lane
        for child in primary_first_children(revision)[1:]:
            if child not in lanes:
                lanes[child] = next_lane
                next_lane += 1

    return lanes


def _normalize_revisions(value: object) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _incoming_revisions(migration) -> List[str]:
    return _normalize_revisions(migration.down_revision) + _normalize_revisions(
        migration.depends_on
    )


def _calculate_cycle_tolerant_layout(graph: GraphState) -> tuple[List[str], Dict[str, int]]:
    revisions = {migration.revision for migration in graph.migrations}
    adjacency = {revision: [] for revision in revisions}

    for migration in graph.migrations:
        for parent in _incoming_revisions(migration):
            if parent in revisions:
                adjacency[parent].append(migration.revision)

    for children in adjacency.values():
        children.sort()

    components = _strongly_connected_components(adjacency)
    component_by_revision = {
        revision: index
        for index, component in enumerate(components)
        for revision in component
    }

    component_adjacency = {index: set() for index in range(len(components))}
    component_in_degree = {index: 0 for index in range(len(components))}

    for parent, children in adjacency.items():
        parent_component = component_by_revision[parent]
        for child in children:
            child_component = component_by_revision[child]
            if child_component == parent_component:
                continue
            if child_component not in component_adjacency[parent_component]:
                component_adjacency[parent_component].add(child_component)
                component_in_degree[child_component] += 1

    queue = deque(
        sorted(
            (index for index, degree in component_in_degree.items() if degree == 0),
            key=lambda index: components[index],
        )
    )
    ordered_components: List[int] = []

    while queue:
        component = queue.popleft()
        ordered_components.append(component)
        for child in sorted(component_adjacency[component], key=lambda index: components[index]):
            component_in_degree[child] -= 1
            if component_in_degree[child] == 0:
                queue.append(child)
        queue = deque(sorted(queue, key=lambda index: components[index]))

    component_layers: Dict[int, int] = {}
    reverse_component_adjacency = {index: set() for index in range(len(components))}
    for parent, children in component_adjacency.items():
        for child in children:
            reverse_component_adjacency[child].add(parent)

    for component in ordered_components:
        parents = reverse_component_adjacency[component]
        component_layers[component] = (
            0 if not parents else max(component_layers[parent] for parent in parents) + 1
        )

    order: List[str] = []
    layers: Dict[str, int] = {}
    for component in ordered_components:
        order.extend(components[component])
        for revision in components[component]:
            layers[revision] = component_layers[component]

    return order, layers


def _strongly_connected_components(adjacency: Dict[str, List[str]]) -> List[List[str]]:
    index = 0
    index_by_revision: Dict[str, int] = {}
    lowlink_by_revision: Dict[str, int] = {}
    stack: List[str] = []
    on_stack: set[str] = set()
    components: List[List[str]] = []

    def visit(revision: str) -> None:
        nonlocal index

        index_by_revision[revision] = index
        lowlink_by_revision[revision] = index
        index += 1
        stack.append(revision)
        on_stack.add(revision)

        for child in adjacency.get(revision, []):
            if child not in index_by_revision:
                visit(child)
                lowlink_by_revision[revision] = min(
                    lowlink_by_revision[revision], lowlink_by_revision[child]
                )
            elif child in on_stack:
                lowlink_by_revision[revision] = min(
                    lowlink_by_revision[revision], index_by_revision[child]
                )

        if lowlink_by_revision[revision] != index_by_revision[revision]:
            return

        component: List[str] = []
        while stack:
            member = stack.pop()
            on_stack.remove(member)
            component.append(member)
            if member == revision:
                break
        components.append(sorted(component))

    for revision in sorted(adjacency):
        if revision not in index_by_revision:
            visit(revision)

    components.sort()
    return components
