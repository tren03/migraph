"""Validation helpers for migration graphs."""

from collections import Counter
from typing import Dict, List, Set

from alembic_viz_contracts.models import GraphState, MigrationNode, ValidationError


def _normalize_revisions(value: object) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _down_revisions(node: MigrationNode) -> List[str]:
    return _normalize_revisions(node.down_revision)


def _dependencies(node: MigrationNode) -> List[str]:
    return _normalize_revisions(node.depends_on)


def _all_incoming_revisions(node: MigrationNode) -> List[str]:
    return _down_revisions(node) + _dependencies(node)


def _node_map(graph: GraphState) -> Dict[str, MigrationNode]:
    return {migration.revision: migration for migration in graph.migrations}


def _adjacency(graph: GraphState) -> Dict[str, List[str]]:
    revisions = {migration.revision for migration in graph.migrations}
    adjacency = {revision: [] for revision in revisions}

    for migration in graph.migrations:
        for parent in _all_incoming_revisions(migration):
            if parent in revisions:
                adjacency[parent].append(migration.revision)

    for children in adjacency.values():
        children.sort()

    return adjacency


def detect_cycles(graph: GraphState) -> List[List[str]]:
    """Return all distinct cycle paths in the graph."""
    adjacency = _adjacency(graph)
    visited: Set[str] = set()
    visiting: List[str] = []
    cycles: List[List[str]] = []
    seen_cycles: Set[tuple[str, ...]] = set()

    def visit(revision: str) -> None:
        if revision in visiting:
            start = visiting.index(revision)
            cycle = visiting[start:] + [revision]
            cycle_key = tuple(cycle)
            if cycle_key not in seen_cycles:
                seen_cycles.add(cycle_key)
                cycles.append(cycle)
            return

        if revision in visited:
            return

        visiting.append(revision)
        for child in adjacency.get(revision, []):
            visit(child)
        visiting.pop()
        visited.add(revision)

    for revision in sorted(adjacency):
        visit(revision)

    return cycles


def detect_heads(graph: GraphState) -> List[str]:
    """Return revisions with no children through down_revision edges."""
    revisions = {migration.revision for migration in graph.migrations}
    referenced = {
        parent
        for migration in graph.migrations
        for parent in _down_revisions(migration)
        if parent in revisions
    }
    return sorted(revisions - referenced)


def detect_orphans(graph: GraphState) -> List[str]:
    """Return revisions that reference missing parents or dependencies."""
    revisions = {migration.revision for migration in graph.migrations}
    orphans = []

    for migration in graph.migrations:
        if any(parent not in revisions for parent in _all_incoming_revisions(migration)):
            orphans.append(migration.revision)

    return sorted(orphans)


def validate(graph: GraphState) -> List[ValidationError]:
    """Validate the graph for duplicate revisions, orphans, and cycles."""
    errors: List[ValidationError] = []

    duplicate_counts = Counter(migration.revision for migration in graph.migrations)
    for revision, count in sorted(duplicate_counts.items()):
        if count > 1:
            errors.append(
                ValidationError(
                    type="duplicate_revision",
                    message=f"Revision {revision} appears {count} times.",
                    details={"revision": revision, "count": count},
                )
            )

    node_map = _node_map(graph)
    for revision in detect_orphans(graph):
        migration = node_map[revision]
        missing = [parent for parent in _all_incoming_revisions(migration) if parent not in node_map]
        errors.append(
            ValidationError(
                type="orphan",
                message=f"Revision {revision} references missing revisions: {', '.join(sorted(missing))}.",
                details={"revision": revision, "missing_revisions": sorted(missing)},
            )
        )

    for cycle in detect_cycles(graph):
        errors.append(
            ValidationError(
                type="cycle",
                message=f"Cycle detected: {' -> '.join(cycle)}.",
                details={"path": cycle},
            )
        )

    return errors
