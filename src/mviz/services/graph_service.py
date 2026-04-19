"""Graph service - business logic for graph operations."""

from collections import Counter, deque
from typing import Any, Dict, List, Set

from mviz.domain.models import GraphState, MigrationNode, ValidationError


class GraphService:
    """Service for graph operations and validation."""

    def validate(self, graph: GraphState) -> List[ValidationError]:
        """Validate the graph for duplicates, orphans, and cycles."""
        errors: List[ValidationError] = []

        # Check for duplicate revisions
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

        # Check for orphans
        node_map = self._node_map(graph)
        for revision in self._detect_orphans(graph):
            migration = node_map[revision]
            missing = [
                parent
                for parent in self._all_incoming_revisions(migration)
                if parent not in node_map
            ]
            errors.append(
                ValidationError(
                    type="orphan",
                    message=f"Revision {revision} references missing revisions: {', '.join(sorted(missing))}.",
                    details={
                        "revision": revision,
                        "missing_revisions": sorted(missing),
                    },
                )
            )

        # Check for cycles
        for cycle in self._detect_cycles(graph):
            errors.append(
                ValidationError(
                    type="cycle",
                    message=f"Cycle detected: {' -> '.join(cycle)}.",
                    details={"path": cycle},
                )
            )

        return errors

    def detect_heads(self, graph: GraphState) -> List[str]:
        """Return revisions with no children through down_revision edges."""
        revisions = {migration.revision for migration in graph.migrations}
        referenced = {
            parent
            for migration in graph.migrations
            for parent in self._down_revisions(migration)
            if parent in revisions
        }
        return sorted(revisions - referenced)

    def detect_orphans(self, graph: GraphState) -> List[str]:
        """Return revisions that reference missing parents."""
        return self._detect_orphans(graph)

    def detect_cycles(self, graph: GraphState) -> List[List[str]]:
        """Return all distinct cycle paths in the graph."""
        return self._detect_cycles(graph)

    def topological_sort(self, graph: GraphState) -> List[str]:
        """Return a stable topological ordering of revisions."""
        cycles = self._detect_cycles(graph)
        if cycles:
            raise ValueError(
                f"Cannot topologically sort cyclic graph: {' -> '.join(cycles[0])}"
            )

        adjacency, in_degree = self._graph_edges(graph)
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

    def calculate_layers(self, graph: GraphState) -> Dict[str, int]:
        """Assign each revision to a layer based on its deepest ancestor."""
        layers: Dict[str, int] = {}
        node_map = self._node_map(graph)

        for revision in self.topological_sort(graph):
            parents = [
                parent
                for parent in self._all_incoming_revisions(node_map[revision])
                if parent in node_map
            ]
            if not parents:
                layers[revision] = 0
            else:
                layers[revision] = max(layers[parent] for parent in parents) + 1

        return layers

    def _normalize_revisions(self, value: object) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [item for item in value if isinstance(item, str)]
        return []

    def _down_revisions(self, node: MigrationNode) -> List[str]:
        return self._normalize_revisions(node.down_revision)

    def _dependencies(self, node: MigrationNode) -> List[str]:
        return self._normalize_revisions(node.depends_on)

    def _all_incoming_revisions(self, node: MigrationNode) -> List[str]:
        return self._down_revisions(node) + self._dependencies(node)

    def _node_map(self, graph: GraphState) -> Dict[str, MigrationNode]:
        return {migration.revision: migration for migration in graph.migrations}

    def _adjacency(self, graph: GraphState) -> Dict[str, List[str]]:
        revisions = {migration.revision for migration in graph.migrations}
        adjacency = {revision: [] for revision in revisions}
        for migration in graph.migrations:
            for parent in self._all_incoming_revisions(migration):
                if parent in revisions:
                    adjacency[parent].append(migration.revision)
        for children in adjacency.values():
            children.sort()
        return adjacency

    def _graph_edges(
        self, graph: GraphState
    ) -> tuple[Dict[str, List[str]], Dict[str, int]]:
        revisions = set(self._node_map(graph))
        adjacency = {revision: [] for revision in revisions}
        in_degree = {revision: 0 for revision in revisions}

        for migration in graph.migrations:
            for parent in self._all_incoming_revisions(migration):
                if parent in revisions:
                    adjacency[parent].append(migration.revision)
                    in_degree[migration.revision] += 1

        for children in adjacency.values():
            children.sort()

        return adjacency, in_degree

    def _detect_orphans(self, graph: GraphState) -> List[str]:
        revisions = {migration.revision for migration in graph.migrations}
        orphans = []
        for migration in graph.migrations:
            if any(
                parent not in revisions
                for parent in self._all_incoming_revisions(migration)
            ):
                orphans.append(migration.revision)
        return sorted(orphans)

    def _detect_cycles(self, graph: GraphState) -> List[List[str]]:
        adjacency = self._adjacency(graph)
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
