"""Diff helpers for comparing graph states."""

from dataclasses import dataclass
from typing import List, Sequence, Union

from alembic_viz_contracts.models import GraphState, MigrationNode


def _normalize_revisions(value: object) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _parent_set(node: MigrationNode) -> set[str]:
    return set(_normalize_revisions(node.down_revision))


@dataclass(frozen=True)
class AddEdge:
    parent_revision: str
    child_revision: str


@dataclass(frozen=True)
class RemoveEdge:
    parent_revision: str
    child_revision: str


@dataclass(frozen=True)
class ChangeParent:
    revision: str
    old_parents: Sequence[str]
    new_parents: Sequence[str]


@dataclass(frozen=True)
class AddedMigration:
    revision: str


@dataclass(frozen=True)
class RemovedMigration:
    revision: str


Operation = Union[AddEdge, RemoveEdge, ChangeParent, AddedMigration, RemovedMigration]


def diff(old: GraphState, new: GraphState) -> List[Operation]:
    """Return graph operations needed to transform old into new."""
    old_nodes = {migration.revision: migration for migration in old.migrations}
    new_nodes = {migration.revision: migration for migration in new.migrations}
    operations: List[Operation] = []

    for revision in sorted(old_nodes.keys() - new_nodes.keys()):
        operations.append(RemovedMigration(revision=revision))

    for revision in sorted(new_nodes.keys() - old_nodes.keys()):
        operations.append(AddedMigration(revision=revision))

    for revision in sorted(old_nodes.keys() & new_nodes.keys()):
        old_parents = _parent_set(old_nodes[revision])
        new_parents = _parent_set(new_nodes[revision])
        if old_parents == new_parents:
            continue

        operations.append(
            ChangeParent(
                revision=revision,
                old_parents=tuple(sorted(old_parents)),
                new_parents=tuple(sorted(new_parents)),
            )
        )

        for parent in sorted(old_parents - new_parents):
            operations.append(RemoveEdge(parent_revision=parent, child_revision=revision))

        for parent in sorted(new_parents - old_parents):
            operations.append(AddEdge(parent_revision=parent, child_revision=revision))

    return operations
